from __future__ import annotations

import json
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from PIL import Image

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

from .config import Settings, get_settings
from .model_assets import resolve_assets
from .inference import (
    bbox_to_json,
    embedding_to_json,
    extract_item_embedding,
    load_models,
    analyze_single_item,
    score_outfit_embeddings,
    score_outfit_compatibility,
)
from .storage import (
    WardrobeItem,
    increment_times_worn,
    init_db,
    insert_item,
    list_items,
    list_liked_outfits,
    delete_liked_outfit,
    get_item,
    record_outfit_feedback,
    update_item,
    delete_item,
    to_api_dict,
)
from .vector_index import VectorIndex
from .recommendation import (
    VALID_EVENTS,
    VALID_MOODS,
    VALID_WEATHERS,
    WEATHER_MAP,
    EVENT_MAP,
    MOOD_MAP,
    RecommendContext,
    generate_recommendations,
)
from .weather import fetch_current_weather


def create_app() -> Flask:
    settings = get_settings()

    app = Flask(__name__)
    CORS(app)

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    init_db(settings.db_path)

    assets = resolve_assets(settings.model_dir)
    models = load_models(assets)

    def _open_image(path: str) -> Image.Image:
        """Open an image file safely, with a clear error for unsupported formats."""
        p = Path(path)
        if p.suffix.lower() in {".heic", ".heif"}:
            try:
                return Image.open(path).convert("RGB")
            except Exception as e:
                raise RuntimeError(
                    "HEIC/HEIF format not supported. "
                    "Install pillow-heif: `.venv\\Scripts\\pip install pillow-heif` "
                    "then restart the backend."
                ) from e
        try:
            return Image.open(path).convert("RGB")
        except Exception as e:
            raise RuntimeError(f"Cannot open image '{p.name}': {e}") from e

    def _embedding_from_image(image: Image.Image, bbox: list[float] | None) -> str | None:
        embedding = extract_item_embedding(models=models, image=image, bbox=bbox)
        return embedding_to_json(embedding) if embedding is not None else None

    def _backfill_missing_embeddings() -> None:
        for item in list_items(settings.db_path):
            if item.embedding_json:
                continue
            try:
                bbox = json.loads(item.bbox_json) if item.bbox_json else None
                image = _open_image(item.image_path)
                embedding_json = _embedding_from_image(image, bbox)
                if embedding_json is not None:
                    update_item(settings.db_path, item.id, embedding_json=embedding_json)
            except Exception:
                continue

    _backfill_missing_embeddings()

    def _build_vector_index() -> VectorIndex | None:
        indexed: VectorIndex | None = None
        for item in list_items(settings.db_path):
            if not item.embedding_json:
                continue
            try:
                embedding = [float(x) for x in json.loads(item.embedding_json)]
                if indexed is None:
                    indexed = VectorIndex(dimension=len(embedding))
                indexed.add(item.id, embedding)
            except Exception:
                continue
        return indexed

    # Persistent vector index — built once at startup, refreshed whenever the
    # wardrobe changes (upload / delete / reanalyze). Using a list wrapper so
    # nested endpoint functions can mutate it without a `global` declaration.
    _index_ref: list = [_build_vector_index()]

    def _get_vector_index() -> VectorIndex | None:
        """Return the current in-memory vector index (may be None if no embeddings exist)."""
        return _index_ref[0]

    def _refresh_vector_index() -> None:
        """Rebuild the vector index from the current wardrobe. Called after any write."""
        _index_ref[0] = _build_vector_index()

    # Debug: help identify which source files are running.
    try:
        from . import inference as _inference_mod

        api_file = Path(__file__).resolve()
        inference_file_raw = getattr(_inference_mod, "__file__", None)
        inference_file = Path(inference_file_raw).resolve() if inference_file_raw else None

        debug_info = {
            "api_file": str(api_file),
            "api_mtime": api_file.stat().st_mtime,
            "inference_file": str(inference_file) if inference_file else None,
            "inference_mtime": inference_file.stat().st_mtime if inference_file and inference_file.exists() else None,
        }
    except Exception as e:
        debug_info = {"error": str(e)}

    def _base_url() -> str:
        # Honor reverse-proxy / forwarded headers as a best effort
        host = request.host_url.rstrip("/")
        return host

    def _outfit_items_to_urls(outfits: list[dict]) -> None:
        base = _base_url()
        for outfit in outfits:
            for it in outfit["items"]:
                filename = Path(it["image_path"]).name
                it["image_url"] = f"{base}/uploads/{filename}"
                del it["image_path"]

    def _mark_recommended_items_worn(outfits: list[dict]) -> None:
        item_ids = [
            str(item["id"])
            for outfit in outfits
            for item in outfit.get("items", [])
            if not str(item.get("id", "")).startswith("preview-")
        ]
        if item_ids:
            increment_times_worn(settings.db_path, item_ids)

    def get_preview_item(
        *,
        item_id: str,
        image_path: str,
        main_category: str,
        sub_category: str,
        bbox_json: str | None,
        embedding_json: str | None,
        model_confidence: float | None,
    ) -> WardrobeItem:
        return WardrobeItem(
            id=item_id,
            image_path=image_path,
            main_category=main_category,
            sub_category=sub_category,
            manual_override=False,
            bbox_json=bbox_json,
            embedding_json=embedding_json,
            model_confidence=float(model_confidence) if model_confidence is not None else None,
            favorite=False,
            times_worn=0,
            created_at="",
            updated_at="",
        )

    @app.route("/health", methods=["GET"])
    def health() -> tuple[dict, int]:
        return (
            jsonify(
                {
                    "status": "healthy",
                    "models": {
                        "yolo_loaded": models.yolo is not None,
                        "resnet18_loaded": models.resnet18_subcat is not None,
                        "resnet50_loaded": models.resnet50_compat is not None,
                    },
                    "paths": {
                        "model_dir": str(settings.model_dir),
                        "upload_dir": str(settings.upload_dir),
                        "db_path": str(settings.db_path),
                        "yolo_path": str(assets.yolo_path),
                        "resnet18_subcat_path": str(assets.resnet18_subcat_path),
                        "resnet50_compat_path": str(assets.resnet50_compat_path),
                        "subcat_mapping": str(assets.subcat_mapping_path),
                        "subcat_to_main": str(assets.subcat_to_main_path),
                        "main_to_subcat_ids": str(assets.main_to_subcat_ids_path),
                    },
                    "errors": models.errors,
                    "warnings": models.warnings,
                    "vector_index_backend": (_get_vector_index().backend if _get_vector_index() else None),
                    "debug": debug_info,
                    "yolo_conf": settings.yolo_conf,
                    "yolo_iou": settings.yolo_iou,
                }
            ),
            200,
        )

    @app.route("/uploads/<path:filename>", methods=["GET"])
    def get_upload(filename: str):
        return send_from_directory(str(settings.upload_dir), filename)

    @app.route("/metadata/categories", methods=["GET"])
    def category_metadata():
        subcategories_by_main: dict[str, list[str]] = {main: [] for main in settings.yolo_main_categories}

        if models.subcat_mapping and models.main_to_subcat_ids:
            for main, ids in models.main_to_subcat_ids.items():
                names: list[str] = []
                for subcat_id in ids:
                    name = models.subcat_mapping.get(str(subcat_id))
                    if isinstance(name, str):
                        names.append(name)
                subcategories_by_main[main] = sorted(set(names))

        return (
            jsonify(
                {
                    "main_categories": list(settings.yolo_main_categories),
                    "subcategories_by_main": subcategories_by_main,
                    "weather_types": list(VALID_WEATHERS),
                    "event_types": list(VALID_EVENTS),
                    "mood_types": list(VALID_MOODS),
                    "model_dir": str(settings.model_dir),
                }
            ),
            200,
        )

    @app.route("/weather/current", methods=["GET"])
    def current_weather():
        try:
            latitude = float(request.args.get("latitude", ""))
            longitude = float(request.args.get("longitude", ""))
        except ValueError:
            return jsonify({"error": "latitude and longitude are required numbers"}), 400

        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            return jsonify({"error": "latitude or longitude is out of range"}), 400

        try:
            result = fetch_current_weather(latitude, longitude)
        except Exception as e:
            return jsonify({"error": f"Weather provider unavailable: {e}"}), 502

        return (
            jsonify(
                {
                    "weather": result.weather,
                    "temperature_c": result.temperature_c,
                    "precipitation_mm": result.precipitation_mm,
                    "weather_code": result.weather_code,
                    "description": result.description,
                    "provider": result.provider,
                }
            ),
            200,
        )

    # --- Wardrobe endpoints (guide) ---

    @app.route("/wardrobe/items", methods=["POST"])
    def upload_wardrobe_item():
        if "image" not in request.files:
            return jsonify({"error": "No image provided"}), 400

        forced_main_category = request.form.get("forced_main_category")
        if forced_main_category:
            forced_main_category = forced_main_category.strip().lower()

        image_file = request.files["image"]
        image = Image.open(image_file.stream)

        analysis = analyze_single_item(
            models=models,
            image=image,
            yolo_conf=settings.yolo_conf,
            yolo_iou=settings.yolo_iou,
            yolo_main_categories=settings.yolo_main_categories,
            forced_main_category=forced_main_category,
        )

        item_id = str(uuid.uuid4())
        filename = f"{item_id}.jpg"
        out_path = settings.upload_dir / filename
        image.convert("RGB").save(out_path, format="JPEG", quality=90)

        bbox_json = bbox_to_json(analysis["bbox"])
        embedding_json = _embedding_from_image(image, analysis["bbox"])
        model_conf = analysis.get("model_confidence")

        item = insert_item(
            settings.db_path,
            item_id=item_id,
            image_path=str(out_path),
            main_category=analysis["main_category"],
            sub_category=analysis["sub_category"],
            bbox_json=bbox_json,
            embedding_json=embedding_json,
            model_confidence=float(model_conf) if model_conf is not None else None,
        )

        # New item has an embedding — rebuild index so style-search finds it immediately.
        _refresh_vector_index()

        base = _base_url()
        payload = to_api_dict(item, base_url=base)
        payload["bbox"] = analysis["bbox"]
        return jsonify(payload), 200

    @app.route("/wardrobe/items", methods=["GET"])
    def list_wardrobe():
        base = _base_url()
        items = [to_api_dict(i, base_url=base) for i in list_items(settings.db_path)]
        return jsonify(items), 200

    @app.route("/wardrobe/vector-search", methods=["POST"])
    def vector_search():
        body = request.get_json(silent=True) or {}
        embedding = body.get("embedding")
        if not isinstance(embedding, list):
            return jsonify({"error": "embedding must be a list"}), 400
        top_k = int(body.get("top_k", 5))
        index = _build_vector_index()
        if index is None:
            return jsonify({"backend": None, "results": []}), 200
        try:
            results = index.search([float(x) for x in embedding], top_k=top_k)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        return jsonify(
            {
                "backend": index.backend,
                "results": [
                    {"id": result.item_id, "score": result.score}
                    for result in results
                ],
            }
        ), 200

    @app.route("/wardrobe/items/<item_id>", methods=["PATCH"])
    def patch_item(item_id: str):
        body = request.get_json(silent=True) or {}

        main_category = body.get("main_category")
        sub_category = body.get("sub_category")
        manual_override = body.get("manual_override")
        favorite = body.get("favorite")
        times_worn = body.get("times_worn")

        if main_category is not None:
            main_category = str(main_category).strip().lower()
        if sub_category is not None:
            sub_category = str(sub_category).strip()
        if manual_override is not None:
            manual_override = bool(manual_override)
        if favorite is not None:
            favorite = bool(favorite)
        if times_worn is not None:
            try:
                times_worn = int(times_worn)
            except (TypeError, ValueError):
                return jsonify({"error": "times_worn must be an integer"}), 400

        try:
            item = update_item(
                settings.db_path,
                item_id,
                main_category=main_category,
                sub_category=sub_category,
                manual_override=manual_override,
                favorite=favorite,
                times_worn=times_worn,
            )
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except KeyError:
            return jsonify({"error": "Item not found"}), 404

        return jsonify(to_api_dict(item, base_url=_base_url())), 200

    @app.route("/wardrobe/items/<item_id>/wear", methods=["POST"])
    def mark_item_worn(item_id: str):
        try:
            item = get_item(settings.db_path, item_id)
            updated = update_item(settings.db_path, item_id, times_worn=item.times_worn + 1)
        except KeyError:
            return jsonify({"error": "Item not found"}), 404
        return jsonify(to_api_dict(updated, base_url=_base_url())), 200

    @app.route("/wardrobe/items/<item_id>", methods=["DELETE"])
    def remove_item(item_id: str):
        try:
            item = get_item(settings.db_path, item_id)
        except KeyError:
            return jsonify({"error": "Item not found"}), 404

        # Delete DB record
        delete_item(settings.db_path, item_id)

        # Best-effort delete image
        try:
            Path(item.image_path).unlink(missing_ok=True)
        except Exception:
            pass

        # Item removed — rebuild index so it no longer appears in style-search.
        _refresh_vector_index()

        return jsonify({"success": True}), 200

    @app.route("/wardrobe/items/<item_id>/reanalyze", methods=["POST"])
    def reanalyze_item(item_id: str):
        try:
            item = get_item(settings.db_path, item_id)
        except KeyError:
            return jsonify({"error": "Item not found"}), 404

        try:
            forced_main_category = request.args.get("forced_main_category")
            if forced_main_category:
                forced_main_category = forced_main_category.strip().lower()

            image = _open_image(item.image_path)
            analysis = analyze_single_item(
                models=models,
                image=image,
                yolo_conf=settings.yolo_conf,
                yolo_iou=settings.yolo_iou,
                yolo_main_categories=settings.yolo_main_categories,
                forced_main_category=forced_main_category,
            )

            bbox_json = bbox_to_json(analysis["bbox"])
            embedding_json = _embedding_from_image(image, analysis["bbox"])
            model_conf = analysis.get("model_confidence")

            updated = update_item(
                settings.db_path,
                item_id,
                main_category=analysis["main_category"],
                sub_category=analysis["sub_category"],
                manual_override=False,
                bbox_json=bbox_json,
                embedding_json=embedding_json,
                model_confidence=float(model_conf) if model_conf is not None else None,
            )

            # Embedding may have changed — rebuild index so the updated
            # representation is used in future style-search queries.
            _refresh_vector_index()

            payload = to_api_dict(updated, base_url=_base_url())
            payload["bbox"] = analysis["bbox"]
            return jsonify(payload), 200
        except FileNotFoundError:
            return jsonify({"error": "Image file not found on server"}), 404
        except Exception as exc:
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Reanalysis failed: {exc}"}), 500

    # --- Recommendations (guide) ---

    @app.route("/recommendations", methods=["POST"])
    def recommend():
        body = request.get_json(silent=True) or {}
        anchor_item_id = body.get("anchor_item_id")
        if anchor_item_id is not None:
            anchor_item_id = str(anchor_item_id).strip() or None
        exclude_item_ids_raw = body.get("exclude_item_ids", [])
        exclude_item_ids = {
            str(item_id).strip()
            for item_id in exclude_item_ids_raw
            if str(item_id).strip()
        } if isinstance(exclude_item_ids_raw, list) else set()
        ctx = RecommendContext(
            weather=str(body.get("weather", "mild")).strip().lower(),
            event=str(body.get("event", "casual")).strip().lower(),
            mood=str(body.get("mood", "relaxed")).strip().lower(),
            gender=str(body.get("gender", "no preference")).strip().lower(),
            outerwear_required=bool(body.get("outerwear_required", False)),
        )

        wardrobe = list_items(settings.db_path)

        def model_scorer(items):
            embeddings = []
            image_paths = []
            for item in items:
                if item.embedding_json:
                    try:
                        embedding = json.loads(item.embedding_json)
                        if isinstance(embedding, list):
                            embeddings.append([float(x) for x in embedding])
                    except Exception:
                        pass
                image_paths.append(item.image_path)

            if len(embeddings) == len(items):
                return score_outfit_embeddings(models=models, embeddings=embeddings)
            return score_outfit_compatibility(models=models, image_paths=image_paths)

        outfits = generate_recommendations(
            wardrobe_items=wardrobe,
            ctx=ctx,
            anchor_item_id=anchor_item_id,
            exclude_item_ids=exclude_item_ids,
            top_k=1,
            model_scorer=model_scorer,
        )

        _mark_recommended_items_worn(outfits)
        _outfit_items_to_urls(outfits)

        return jsonify({"outfits": outfits}), 200

    @app.route("/recommendations/preview", methods=["POST"])
    def preview_recommendation():
        if "image" not in request.files:
            return jsonify({"error": "No image provided"}), 400

        forced_main_category = request.form.get("forced_main_category")
        if forced_main_category:
            forced_main_category = forced_main_category.strip().lower()
        ctx = RecommendContext(
            weather=str(request.form.get("weather", "mild")).strip().lower(),
            event=str(request.form.get("event", "casual")).strip().lower(),
            mood=str(request.form.get("mood", "relaxed")).strip().lower(),
            gender=str(request.form.get("gender", "no preference")).strip().lower(),
            outerwear_required=str(request.form.get("outerwear_required", "false")).lower() == "true",
        )

        image_file = request.files["image"]
        image = Image.open(image_file.stream)
        analysis = analyze_single_item(
            models=models,
            image=image,
            yolo_conf=settings.yolo_conf,
            yolo_iou=settings.yolo_iou,
            yolo_main_categories=settings.yolo_main_categories,
            forced_main_category=forced_main_category,
        )

        item_id = f"preview-{uuid.uuid4()}"
        filename = f"{item_id}.jpg"
        out_path = settings.upload_dir / filename
        image.convert("RGB").save(out_path, format="JPEG", quality=90)
        transient = get_preview_item(
            item_id=item_id,
            image_path=str(out_path),
            main_category=analysis["main_category"],
            sub_category=analysis["sub_category"],
            bbox_json=bbox_to_json(analysis["bbox"]),
            embedding_json=_embedding_from_image(image, analysis["bbox"]),
            model_confidence=analysis.get("model_confidence"),
        )

        wardrobe = list_items(settings.db_path) + [transient]

        def model_scorer(items):
            embeddings = []
            image_paths = []
            for item in items:
                if item.embedding_json:
                    try:
                        embedding = json.loads(item.embedding_json)
                        if isinstance(embedding, list):
                            embeddings.append([float(x) for x in embedding])
                    except Exception:
                        pass
                image_paths.append(item.image_path)
            if len(embeddings) == len(items):
                return score_outfit_embeddings(models=models, embeddings=embeddings)
            return score_outfit_compatibility(models=models, image_paths=image_paths)

        outfits = generate_recommendations(
            wardrobe_items=wardrobe,
            ctx=ctx,
            anchor_item_id=item_id,
            top_k=1,
            model_scorer=model_scorer,
        )
        _mark_recommended_items_worn(outfits)
        _outfit_items_to_urls(outfits)
        return jsonify({"outfits": outfits}), 200

    @app.route("/recommendations/feedback", methods=["POST"])
    def recommendation_feedback():
        body = request.get_json(silent=True) or {}
        action = str(body.get("action", "")).strip().lower()
        if action not in {"save", "like", "dislike"}:
            return jsonify({"error": "action must be save, like, or dislike"}), 400
        item_ids = body.get("item_ids", [])
        if not isinstance(item_ids, list):
            return jsonify({"error": "item_ids must be a list"}), 400
        score = body.get("score")
        if score is not None:
            try:
                score = float(score)
            except (TypeError, ValueError):
                return jsonify({"error": "score must be a number"}), 400
        feedback = record_outfit_feedback(
            settings.db_path,
            action=action,
            item_ids=[str(item_id) for item_id in item_ids],
            score=score,
        )
        return jsonify({"success": True, **feedback}), 200

    @app.route("/recommendations/liked", methods=["GET"])
    def liked_recommendations():
        base = _base_url()
        item_by_id = {item.id: item for item in list_items(settings.db_path)}
        outfits = []
        for liked in list_liked_outfits(settings.db_path):
            items = [
                to_api_dict(item_by_id[item_id], base_url=base)
                for item_id in liked["item_ids"]
                if item_id in item_by_id
            ]
            if items:
                outfits.append({**liked, "items": items})
        return jsonify({"outfits": outfits}), 200

    @app.route("/recommendations/liked/<feedback_id>", methods=["DELETE"])
    def delete_liked_recommendation(feedback_id: str):
        deleted = delete_liked_outfit(settings.db_path, feedback_id)
        if not deleted:
            return jsonify({"error": "Not found"}), 404
        return jsonify({"success": True}), 200

    def _context_appropriate_ids(wardrobe: list[WardrobeItem], ctx: RecommendContext) -> set[str]:
        """Return IDs of items whose subcategory is valid for the given context.

        An item is considered context-appropriate when its subcategory appears
        in at least one of the weather / event / mood maps for its main category.
        Items with sub_category='unknown' or whose category has no mapping are
        always included so they don't silently vanish from the pool.
        """
        appropriate: set[str] = set()
        for item in wardrobe:
            main = item.main_category.strip().lower()
            sub = item.sub_category.strip().lower()

            weather_subs = set(WEATHER_MAP.get(ctx.weather, {}).get(main, []))
            event_subs = set(EVENT_MAP.get(ctx.event, {}).get(main, []))
            mood_subs = set(MOOD_MAP.get(ctx.mood, {}).get(main, []))
            all_subs = weather_subs | event_subs | mood_subs

            # No mapping for this category → always include (e.g. accessories).
            # Unknown subcategory → include so the item isn't silently dropped.
            if not all_subs or sub == "unknown" or sub in all_subs:
                appropriate.add(item.id)

        return appropriate

    # ── Embedding-based "Similar outfit" recommendation ─────────────────────────
    #
    # How it works:
    #   1. Compute the centroid (average) of the ResNet50 embeddings for the
    #      items in the current outfit — this vector represents its visual style.
    #   2. Search the vector index for the top-N wardrobe items nearest to that
    #      centroid (cosine similarity via L2-normalised dot product).
    #   3. Restrict the recommendation pool to those visually similar items.
    #   4. Run the normal context-aware recommendation on the restricted pool.
    #
    # Result: the suggested outfit shares colour palette, texture, and overall
    # aesthetic with the original — not just random differently-excluded items.
    @app.route("/recommendations/similar", methods=["POST"])
    def similar_recommendations():
        body = request.get_json(silent=True) or {}
        outfit_item_ids: list[str] = [str(x) for x in body.get("outfit_item_ids", [])]
        ctx = RecommendContext(
            weather=str(body.get("weather", "mild")).strip().lower(),
            event=str(body.get("event", "casual")).strip().lower(),
            mood=str(body.get("mood", "relaxed")).strip().lower(),
            gender=str(body.get("gender", "no preference")).strip().lower(),
            outerwear_required=bool(body.get("outerwear_required", False)),
        )

        wardrobe = list_items(settings.db_path)
        item_by_id = {item.id: item for item in wardrobe}

        # Build centroid embedding from the outfit items that have embeddings.
        embeddings: list[list[float]] = []
        for item_id in outfit_item_ids:
            item = item_by_id.get(item_id)
            if item and item.embedding_json:
                try:
                    emb = json.loads(item.embedding_json)
                    if isinstance(emb, list):
                        embeddings.append([float(x) for x in emb])
                except Exception:
                    pass

        # Pre-filter by context so that the similar-item pool only contains
        # items that are appropriate for the selected weather / event / mood.
        # Without this, a "cold + formal" request could receive casual or
        # summery items just because their embeddings happen to be close.
        context_ids = _context_appropriate_ids(wardrobe, ctx)

        filtered_wardrobe = [item for item in wardrobe if item.id in context_ids]
        if embeddings:
            dim = len(embeddings[0])
            n = len(embeddings)
            centroid = [sum(e[i] for e in embeddings) / n for i in range(dim)]

            index = _get_vector_index()
            if index is not None:
                try:
                    # Fetch many candidates — category filter and outfit-exclusion
                    # will discard some, so we need a generous initial set.
                    similar = index.search(centroid, top_k=40)
                    outfit_id_set = set(outfit_item_ids)
                    similar_ids = {
                        r.item_id for r in similar
                        if r.item_id not in outfit_id_set
                        and r.item_id in context_ids  # hard context constraint
                    }
                    similar_items = [item for item in wardrobe if item.id in similar_ids]
                    # Only restrict the pool when there are enough items to form
                    # at least one complete outfit (tops + bottoms + shoes).
                    if len(similar_items) >= 3:
                        filtered_wardrobe = similar_items
                except Exception:
                    pass  # Fall back to context-filtered wardrobe on index error.

        def model_scorer(items):
            embeddings_inner = []
            image_paths = []
            for item in items:
                if item.embedding_json:
                    try:
                        emb = json.loads(item.embedding_json)
                        if isinstance(emb, list):
                            embeddings_inner.append([float(x) for x in emb])
                    except Exception:
                        pass
                image_paths.append(item.image_path)
            if len(embeddings_inner) == len(items):
                return score_outfit_embeddings(models=models, embeddings=embeddings_inner)
            return score_outfit_compatibility(models=models, image_paths=image_paths)

        outfits = generate_recommendations(
            wardrobe_items=filtered_wardrobe,
            ctx=ctx,
            exclude_item_ids=set(outfit_item_ids),
            top_k=1,
            model_scorer=model_scorer,
        )

        if not outfits:
            # Similar pool was too narrow — retry with the full context-filtered wardrobe.
            outfits = generate_recommendations(
                wardrobe_items=[item for item in wardrobe if item.id in context_ids],
                ctx=ctx,
                exclude_item_ids=set(outfit_item_ids),
                top_k=1,
                model_scorer=model_scorer,
            )

        _mark_recommended_items_worn(outfits)
        _outfit_items_to_urls(outfits)
        return jsonify({"outfits": outfits}), 200

    # ── Style-based wardrobe search ("Do I own something like this?") ──────────
    #
    # Use-case: user is shopping online or in a store and wonders whether they
    # already own something visually similar.  They photograph the item and this
    # endpoint returns the closest matches from their wardrobe — no item is saved.
    #
    # How it works:
    #   1. YOLO detects the garment bounding box in the uploaded photo.
    #   2. ResNet50 extracts a style embedding from the cropped region.
    #   3. The embedding is compared against all indexed wardrobe items via
    #      cosine similarity (the vector index).
    #   4. The top-K matches are returned with their similarity score (0–1).
    @app.route("/wardrobe/style-search", methods=["POST"])
    def style_search():
        if "image" not in request.files:
            return jsonify({"error": "No image provided"}), 400

        image_file = request.files["image"]
        try:
            image = Image.open(image_file.stream).convert("RGB")
        except Exception as e:
            return jsonify({"error": f"Cannot open image: {e}"}), 400

        # Run YOLO + ResNet18 to detect the garment and get its bounding box.
        # The bbox improves the ResNet50 embedding by focusing on the clothing
        # item rather than the whole photo (background, person, etc.).
        forced_main_category = request.form.get("main_category")
        if forced_main_category:
            forced_main_category = forced_main_category.strip().lower()

        detected_category: str | None = None
        detected_subcat: str | None = None
        bbox: list[float] | None = None
        try:
            analysis = analyze_single_item(
                models=models,
                image=image,
                yolo_conf=settings.yolo_conf,
                yolo_iou=settings.yolo_iou,
                yolo_main_categories=settings.yolo_main_categories,
                forced_main_category=forced_main_category,
            )
            bbox = analysis.get("bbox")
            detected_category = analysis.get("main_category")
            sub = analysis.get("sub_category", "").strip().lower()
            detected_subcat = sub if sub and sub != "unknown" else None
        except Exception:
            pass  # No bbox — ResNet50 will embed the full image instead.

        # Extract style embedding from the query photo.
        embedding = extract_item_embedding(models=models, image=image, bbox=bbox)
        if embedding is None:
            return jsonify({
                "error": "Could not extract style embedding — ResNet50 model not loaded"
            }), 503

        index = _get_vector_index()
        if index is None:
            # No wardrobe items have embeddings yet (empty wardrobe or no model).
            return jsonify({"detected_category": detected_category, "items": []}), 200

        # Fetch more candidates than the requested limit because the category
        # filter below may discard items from other categories.
        top_k = min(int(request.form.get("top_k", 3)), 10)
        search_k = top_k * 6
        try:
            results = index.search(embedding, top_k=search_k)
        except Exception as e:
            return jsonify({"error": f"Search failed: {e}"}), 500

        item_by_id = {item.id: item for item in list_items(settings.db_path)}
        base = _base_url()

        # Build two candidate lists from the vector search results:
        #   subcat_matches — same main category AND same subcategory as the query
        #   cat_matches    — same main category only (broader fallback)
        # Subcategory filter is preferred: uploading a "sneaker" photo should
        # return sneakers, not heels. But if the wardrobe has no matching
        # subcategory we fall back to the main-category list so the user still
        # gets relevant results instead of an empty screen.
        subcat_matches: list[dict] = []
        cat_matches: list[dict] = []
        for result in results:
            item = item_by_id.get(result.item_id)
            if item is None:
                continue
            if detected_category and item.main_category.strip().lower() != detected_category:
                continue
            d = to_api_dict(item, base_url=base)
            d["similarity_score"] = round(float(result.score), 4)
            cat_matches.append(d)
            if detected_subcat and item.sub_category.strip().lower() == detected_subcat:
                subcat_matches.append(d)

        final_items = subcat_matches if subcat_matches else cat_matches

        return jsonify({
            "detected_category": detected_category,
            "detected_subcategory": detected_subcat,
            "items": final_items[:top_k],
        }), 200

    # Keep old endpoints for backward compatibility (Flutter existing screen)
    @app.route("/api/analyze", methods=["POST"])
    def legacy_analyze():
        # forward to /wardrobe/items analysis but do not store
        if "image" not in request.files:
            return jsonify({"error": "No image provided"}), 400

        forced_main_category = request.form.get("forced_main_category")
        if forced_main_category:
            forced_main_category = forced_main_category.strip().lower()

        image_file = request.files["image"]
        image = Image.open(image_file.stream)
        analysis = analyze_single_item(
            models=models,
            image=image,
            yolo_conf=settings.yolo_conf,
            yolo_iou=settings.yolo_iou,
            yolo_main_categories=settings.yolo_main_categories,
            forced_main_category=forced_main_category,
        )

        return jsonify(
            {
                "success": True,
                "items": [
                    {
                        "bbox": analysis["bbox"],
                        "yolo_class": analysis["main_category"],
                        "yolo_confidence": analysis.get("yolo_confidence", 0.0),
                        "resnet_category": analysis["sub_category"],
                        "resnet_confidence": analysis.get("model_confidence", 0.0) or 0.0,
                    }
                ],
                "count": 1,
            }
        )

    return app

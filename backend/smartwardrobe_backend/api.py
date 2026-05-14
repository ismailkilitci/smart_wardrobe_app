from __future__ import annotations

import json
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from PIL import Image

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
from .storage import init_db, insert_item, list_items, get_item, update_item, delete_item, to_api_dict
from .recommendation import RecommendContext, generate_recommendations
from .weather import fetch_current_weather


def create_app() -> Flask:
    settings = get_settings()

    app = Flask(__name__)
    CORS(app)

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    init_db(settings.db_path)

    assets = resolve_assets(settings.model_dir)
    models = load_models(assets)

    def _embedding_from_image(image: Image.Image, bbox: list[float] | None) -> str | None:
        embedding = extract_item_embedding(models=models, image=image, bbox=bbox)
        return embedding_to_json(embedding) if embedding is not None else None

    def _backfill_missing_embeddings() -> None:
        for item in list_items(settings.db_path):
            if item.embedding_json:
                continue
            try:
                bbox = json.loads(item.bbox_json) if item.bbox_json else None
                image = Image.open(item.image_path)
                embedding_json = _embedding_from_image(image, bbox)
                if embedding_json is not None:
                    update_item(settings.db_path, item.id, embedding_json=embedding_json)
            except Exception:
                continue

    _backfill_missing_embeddings()

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

        base = _base_url()
        payload = to_api_dict(item, base_url=base)
        payload["bbox"] = analysis["bbox"]
        return jsonify(payload), 200

    @app.route("/wardrobe/items", methods=["GET"])
    def list_wardrobe():
        base = _base_url()
        items = [to_api_dict(i, base_url=base) for i in list_items(settings.db_path)]
        return jsonify(items), 200

    @app.route("/wardrobe/items/<item_id>", methods=["PATCH"])
    def patch_item(item_id: str):
        body = request.get_json(silent=True) or {}

        main_category = body.get("main_category")
        sub_category = body.get("sub_category")
        manual_override = body.get("manual_override")

        if main_category is not None:
            main_category = str(main_category).strip().lower()
        if sub_category is not None:
            sub_category = str(sub_category).strip()
        if manual_override is not None:
            manual_override = bool(manual_override)

        try:
            item = update_item(
                settings.db_path,
                item_id,
                main_category=main_category,
                sub_category=sub_category,
                manual_override=manual_override,
            )
        except KeyError:
            return jsonify({"error": "Item not found"}), 404

        return jsonify(to_api_dict(item, base_url=_base_url())), 200

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

        return jsonify({"success": True}), 200

    @app.route("/wardrobe/items/<item_id>/reanalyze", methods=["POST"])
    def reanalyze_item(item_id: str):
        try:
            item = get_item(settings.db_path, item_id)
        except KeyError:
            return jsonify({"error": "Item not found"}), 404

        forced_main_category = request.args.get("forced_main_category")
        if forced_main_category:
            forced_main_category = forced_main_category.strip().lower()

        image = Image.open(item.image_path)
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

        payload = to_api_dict(updated, base_url=_base_url())
        payload["bbox"] = analysis["bbox"]
        return jsonify(payload), 200

    # --- Recommendations (guide) ---

    @app.route("/recommendations", methods=["POST"])
    def recommend():
        body = request.get_json(silent=True) or {}
        anchor_item_id = body.get("anchor_item_id")
        if anchor_item_id is not None:
            anchor_item_id = str(anchor_item_id).strip() or None
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
            top_k=1,
            model_scorer=model_scorer,
        )

        # Convert image_path -> image_url for API
        base = _base_url()
        for outfit in outfits:
            for it in outfit["items"]:
                filename = Path(it["image_path"]).name
                it["image_url"] = f"{base}/uploads/{filename}"
                del it["image_path"]

        return jsonify({"outfits": outfits}), 200

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

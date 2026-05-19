from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _is_git_lfs_pointer(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        with path.open("rb") as f:
            head = f.read(80)
    except Exception:
        return False
    return head.startswith(b"version https://git-lfs.github.com/spec/v1")


def _move_lfs_pointer_aside(db_path: Path) -> None:
    """If db_path is a Git LFS pointer file, rename it so SQLite can create a real DB."""
    if not _is_git_lfs_pointer(db_path):
        return
    # Keep the pointer for debugging but don't block runtime.
    candidate = db_path.with_name(f"{db_path.name}.lfs")
    if candidate.exists():
        candidate = db_path.with_name(
            f"{db_path.name}.lfs.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        )
    db_path.rename(candidate)


@dataclass(frozen=True)
class WardrobeItem:
    id: str
    image_path: str
    main_category: str
    sub_category: str
    manual_override: bool
    bbox_json: str | None
    embedding_json: str | None
    model_confidence: float | None
    favorite: bool
    times_worn: int
    created_at: str
    updated_at: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _move_lfs_pointer_aside(db_path)
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wardrobe_items (
              id TEXT PRIMARY KEY,
              image_path TEXT NOT NULL,
              main_category TEXT NOT NULL,
              sub_category TEXT NOT NULL,
              manual_override INTEGER NOT NULL,
              bbox_json TEXT NULL,
              embedding_json TEXT NULL,
              model_confidence REAL NULL,
              favorite INTEGER NOT NULL DEFAULT 0,
              times_worn INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS outfit_feedback (
              id TEXT PRIMARY KEY,
              action TEXT NOT NULL,
              item_ids_json TEXT NOT NULL,
              score REAL NULL,
              created_at TEXT NOT NULL
            )
            """
        )
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(wardrobe_items)").fetchall()
        }
        if "embedding_json" not in columns:
            conn.execute("ALTER TABLE wardrobe_items ADD COLUMN embedding_json TEXT NULL")
        if "favorite" not in columns:
            conn.execute("ALTER TABLE wardrobe_items ADD COLUMN favorite INTEGER NOT NULL DEFAULT 0")
        if "times_worn" not in columns:
            conn.execute("ALTER TABLE wardrobe_items ADD COLUMN times_worn INTEGER NOT NULL DEFAULT 0")
        conn.commit()


def insert_item(
    db_path: Path,
    *,
    item_id: str,
    image_path: str,
    main_category: str,
    sub_category: str,
    bbox_json: str | None,
    embedding_json: str | None,
    model_confidence: float | None,
) -> WardrobeItem:
    now = _utc_now_iso()
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            INSERT INTO wardrobe_items(
              id, image_path, main_category, sub_category, manual_override, bbox_json, embedding_json, model_confidence, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (item_id, image_path, main_category, sub_category, 0, bbox_json, embedding_json, model_confidence, now, now),
        )
        conn.commit()

    return get_item(db_path, item_id)


def get_item(db_path: Path, item_id: str) -> WardrobeItem:
    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM wardrobe_items WHERE id = ?",
            (item_id,),
        ).fetchone()

    if row is None:
        raise KeyError(f"Wardrobe item not found: {item_id}")

    return WardrobeItem(
        id=row["id"],
        image_path=row["image_path"],
        main_category=row["main_category"],
        sub_category=row["sub_category"],
        manual_override=bool(row["manual_override"]),
        bbox_json=row["bbox_json"],
        embedding_json=row["embedding_json"],
        model_confidence=row["model_confidence"],
        favorite=bool(row["favorite"]),
        times_worn=int(row["times_worn"] or 0),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def list_items(db_path: Path) -> list[WardrobeItem]:
    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM wardrobe_items ORDER BY created_at DESC"
        ).fetchall()

    return [
        WardrobeItem(
            id=r["id"],
            image_path=r["image_path"],
            main_category=r["main_category"],
            sub_category=r["sub_category"],
            manual_override=bool(r["manual_override"]),
            bbox_json=r["bbox_json"],
            embedding_json=r["embedding_json"],
            model_confidence=r["model_confidence"],
            favorite=bool(r["favorite"]),
            times_worn=int(r["times_worn"] or 0),
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )
        for r in rows
    ]


def update_item(
    db_path: Path,
    item_id: str,
    *,
    main_category: str | None = None,
    sub_category: str | None = None,
    manual_override: bool | None = None,
    bbox_json: str | None = None,
    embedding_json: str | None = None,
    model_confidence: float | None = None,
    favorite: bool | None = None,
    times_worn: int | None = None,
) -> WardrobeItem:
    current = get_item(db_path, item_id)

    new_main = main_category if main_category is not None else current.main_category
    new_sub = sub_category if sub_category is not None else current.sub_category
    new_manual = manual_override if manual_override is not None else current.manual_override

    # bbox/embedding/model_confidence: preserve when omitted.
    new_bbox = bbox_json if bbox_json is not None else current.bbox_json
    new_embedding = embedding_json if embedding_json is not None else current.embedding_json
    new_conf = model_confidence if model_confidence is not None else current.model_confidence
    new_favorite = favorite if favorite is not None else current.favorite
    new_times_worn = times_worn if times_worn is not None else current.times_worn
    if new_times_worn < 0:
        raise ValueError("times_worn cannot be negative")

    now = _utc_now_iso()

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            UPDATE wardrobe_items
            SET main_category=?, sub_category=?, manual_override=?, bbox_json=?, embedding_json=?, model_confidence=?, favorite=?, times_worn=?, updated_at=?
            WHERE id=?
            """,
            (
                new_main,
                new_sub,
                1 if new_manual else 0,
                new_bbox,
                new_embedding,
                new_conf,
                1 if new_favorite else 0,
                int(new_times_worn),
                now,
                item_id,
            ),
        )
        conn.commit()

    return get_item(db_path, item_id)


def delete_item(db_path: Path, item_id: str) -> None:
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("DELETE FROM wardrobe_items WHERE id = ?", (item_id,))
        conn.commit()


def increment_times_worn(db_path: Path, item_ids: list[str]) -> None:
    with sqlite3.connect(str(db_path)) as conn:
        for item_id in item_ids:
            conn.execute(
                "UPDATE wardrobe_items SET times_worn = times_worn + 1, updated_at = ? WHERE id = ?",
                (_utc_now_iso(), item_id),
            )
        conn.commit()


def record_outfit_feedback(
    db_path: Path,
    *,
    action: str,
    item_ids: list[str],
    score: float | None = None,
) -> dict[str, Any]:
    import uuid

    if action not in {"save", "like", "dislike"}:
        raise ValueError("action must be save, like, or dislike")
    now = _utc_now_iso()
    feedback_id = str(uuid.uuid4())
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            INSERT INTO outfit_feedback(id, action, item_ids_json, score, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (feedback_id, action, json.dumps(item_ids), score, now),
        )
        conn.commit()

    increment_times_worn(db_path, item_ids)
    return {
        "id": feedback_id,
        "action": action,
        "item_ids": item_ids,
        "score": score,
        "created_at": now,
    }


def list_liked_outfits(db_path: Path) -> list[dict[str, Any]]:
    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM outfit_feedback
            WHERE action IN ('save', 'like')
            ORDER BY created_at DESC
            """
        ).fetchall()

    out: list[dict[str, Any]] = []
    for row in rows:
        try:
            item_ids = json.loads(row["item_ids_json"])
        except Exception:
            item_ids = []
        out.append(
            {
                "id": row["id"],
                "action": row["action"],
                "item_ids": item_ids,
                "score": row["score"],
                "created_at": row["created_at"],
            }
        )
    return out


def delete_liked_outfit(db_path: Path, feedback_id: str) -> bool:
    with sqlite3.connect(str(db_path)) as conn:
        cur = conn.execute(
            "DELETE FROM outfit_feedback WHERE id = ? AND action IN ('save', 'like')",
            (feedback_id,),
        )
        conn.commit()
        return cur.rowcount > 0


def to_api_dict(item: WardrobeItem, *, base_url: str) -> dict[str, Any]:
    # Expose image via /uploads/<filename>
    filename = Path(item.image_path).name
    image_url = f"{base_url}/uploads/{filename}"

    out: dict[str, Any] = {
        "id": item.id,
        "main_category": item.main_category,
        "sub_category": item.sub_category,
        "image_url": image_url,
        "manual_override": item.manual_override,
        "favorite": item.favorite,
        "times_worn": item.times_worn,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }

    if item.bbox_json is not None:
        try:
            out["bbox"] = json.loads(item.bbox_json)
        except Exception:
            out["bbox"] = item.bbox_json
    if item.model_confidence is not None:
        out["model_confidence"] = item.model_confidence
    if item.embedding_json is not None:
        try:
            out["embedding_dim"] = len(json.loads(item.embedding_json))
        except Exception:
            out["embedding_dim"] = None

    return out

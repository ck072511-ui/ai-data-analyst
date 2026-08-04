from typing import Any, Dict, List, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession


async def paginate(
    session: AsyncSession,
    model: Any,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = None,
    sort_order: str = "desc",
    search: str = None,
    search_fields: List[str] = None,
    base_query: Any = None,
) -> Tuple[List[Any], Dict[str, Any]]:
    """
    Standard reusable cursor pagination helper for SQLAlchemy models.
    Supports dynamic sorting, case-insensitive ilike text search, and total page metadata compilation.
    """
    # 1. Base query setup
    if base_query is None:
        query = select(model)
    else:
        query = base_query

    # 2. Case-insensitive text search filters
    if search and search_fields:
        filters = []
        for field in search_fields:
            attr = getattr(model, field, None)
            if attr is not None:
                filters.append(attr.ilike(f"%{search}%"))
        if filters:
            query = query.where(or_(*filters))

    # 3. Total count execution (using count subquery)
    count_query = select(func.count()).select_from(query.subquery())
    total_items = (await session.execute(count_query)).scalar() or 0

    # 4. Sorting resolution
    if sort_by:
        attr = getattr(model, sort_by, None)
        if attr is not None:
            if sort_order.lower() == "desc":
                query = query.order_by(attr.desc())
            else:
                query = query.order_by(attr.asc())
    elif hasattr(model, "created_at"):
        query = query.order_by(model.created_at.desc())
    elif hasattr(model, "timestamp"):
        query = query.order_by(model.timestamp.desc())
    elif hasattr(model, "started_at"):
        query = query.order_by(model.started_at.desc())

    # 5. Offset limits
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # 6. Execute items query
    items = (await session.execute(query)).scalars().all()

    total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 0

    metadata = {
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }

    return items, metadata

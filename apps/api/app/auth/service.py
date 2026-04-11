from collections.abc import Callable

from fastapi import Header, HTTPException, status


def require_role(required_role: str) -> Callable[[str | None], str]:
    def dependency(x_role: str | None = Header(default=None)) -> str:
        if x_role != required_role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return x_role

    return dependency

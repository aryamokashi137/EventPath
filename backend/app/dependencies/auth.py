from fastapi import Header, HTTPException, status

def require_admin_role(x_user_role: str = Header(default="ADMIN")):
    """
    Dependency that enforces ADMIN role for mutating/administrative endpoints.
    Header `X-User-Role` can be passed as 'ADMIN' or 'USER'.
    If omitted, defaults to 'ADMIN' for backwards compatibility.
    """
    if not x_user_role or x_user_role.upper() != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Administrative privileges ('ADMIN' role) are required for this action."
        )
    return x_user_role.upper()

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const COOKIE = "clinic_token";

// Без cookie сеанса – на страницу входа. Права роли проверяет бэкенд (Т13).
export function proxy(request: NextRequest) {
  const hasToken = request.cookies.has(COOKIE);
  const { pathname, search } = request.nextUrl;
  if (pathname === "/login") {
    return NextResponse.next();
  }
  if (!hasToken) {
    const url = new URL("/login", request.url);
    if (pathname !== "/") url.searchParams.set("next", pathname + search);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\.(?:png|svg|ico|jpg)$).*)"],
};

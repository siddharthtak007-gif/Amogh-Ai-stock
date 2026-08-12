import { NextResponse, type NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/middleware";

export async function middleware(request: NextRequest) {
  if (request.nextUrl.pathname.startsWith("/dashboard")) {
    const isLoggedIn = request.cookies.get("custom_auth")?.value === "1";

    if (isLoggedIn) {
      return NextResponse.next();
    }

    return NextResponse.redirect(new URL("/", request.url));
  }

  return updateSession(request);
}

export const config = {
  matcher: ["/dashboard/:path*"],
};

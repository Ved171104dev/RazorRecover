import {NextRequest,NextResponse} from "next/server";
const protectedRoutes=["/dashboard","/risk","/decisions","/actions","/experiments","/audit","/assistant","/settings"];
export function middleware(req:NextRequest){if(protectedRoutes.some(x=>req.nextUrl.pathname.startsWith(x))&&!req.cookies.get("rr_session"))return NextResponse.redirect(new URL("/login",req.url));return NextResponse.next()}
export const config={matcher:["/dashboard/:path*","/risk/:path*","/decisions/:path*","/actions/:path*","/experiments/:path*","/audit/:path*","/assistant/:path*","/settings/:path*"]};

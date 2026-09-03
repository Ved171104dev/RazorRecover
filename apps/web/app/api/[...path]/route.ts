import { NextRequest } from "next/server";

const API_URL = process.env.API_PROXY_URL?.replace(/\/$/, "");
const RETRY_DELAY_MS = 1_500;
const API_WAKE_WINDOW_MS = 180_000;
const HEALTH_REQUEST_TIMEOUT_MS = 10_000;
let awakeUntil = 0;
let wakePromise: Promise<boolean> | null = null;

const sleep = (milliseconds: number) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds));

async function wakeApi(): Promise<boolean> {
  if (!API_URL) return false;
  if (Date.now() < awakeUntil) return true;
  if (wakePromise) return wakePromise;

  wakePromise = attemptWakeApi();
  try {
    return await wakePromise;
  } finally {
    wakePromise = null;
  }
}

async function attemptWakeApi(): Promise<boolean> {
  const deadline = Date.now() + API_WAKE_WINDOW_MS;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${API_URL}/health`, {
        cache: "no-store",
        signal: AbortSignal.timeout(HEALTH_REQUEST_TIMEOUT_MS),
      });
      if (response.ok) {
        awakeUntil = Date.now() + 30_000;
        return true;
      }
    } catch {
      // A sleeping Render free service can refuse requests while it starts.
    }
    if (Date.now() < deadline) await sleep(RETRY_DELAY_MS);
  }
  return false;
}

function responseHeaders(source: Headers): Headers {
  const headers = new Headers(source);
  const cookies = (
    source as Headers & { getSetCookie?: () => string[] }
  ).getSetCookie?.();
  headers.delete("content-encoding");
  headers.delete("content-length");
  headers.delete("transfer-encoding");
  headers.delete("connection");
  if (cookies?.length) {
    headers.delete("set-cookie");
    cookies.forEach((cookie) => headers.append("set-cookie", cookie));
  }
  return headers;
}

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  if (!API_URL) {
    return Response.json(
      { error: { message: "API connection is not configured" } },
      { status: 503 },
    );
  }

  if (!(await wakeApi())) {
    return Response.json(
      {
        error: {
          message:
            "The free API is still waking up. Please wait a moment and try again.",
        },
      },
      { status: 503 },
    );
  }

  const { path } = await context.params;
  const target = new URL(`${API_URL}/api/${path.join("/")}`);
  target.search = request.nextUrl.search;
  const headers = new Headers(request.headers);
  for (const name of ["host", "connection", "content-length", "transfer-encoding"])
    headers.delete(name);

  try {
    const body =
      request.method === "GET" || request.method === "HEAD"
        ? undefined
        : await request.arrayBuffer();
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
      redirect: "manual",
    });
    return new Response(await upstream.arrayBuffer(), {
      status: upstream.status,
      headers: responseHeaders(upstream.headers),
    });
  } catch {
    awakeUntil = 0;
    return Response.json(
      { error: { message: "The API is temporarily unavailable. Please retry." } },
      { status: 502 },
    );
  }
}

export const dynamic = "force-dynamic";
export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
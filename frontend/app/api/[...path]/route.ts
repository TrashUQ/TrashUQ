import { NextRequest, NextResponse } from "next/server";

const DEFAULT_BACKEND_API_URL = "http://backend:4000";

function getBackendUrl(path: string[]) {
  const baseUrl = process.env.BACKEND_API_URL ?? DEFAULT_BACKEND_API_URL;
  return `${baseUrl.replace(/\/$/, "")}/api/${path.map(encodeURIComponent).join("/")}`;
}

async function proxyRequest(request: NextRequest, context: { params: { path: string[] } }) {
  const upstreamUrl = new URL(getBackendUrl(context.params.path));
  request.nextUrl.searchParams.forEach((value, key) => {
    upstreamUrl.searchParams.append(key, value);
  });

  try {
    const upstream = await fetch(upstreamUrl, {
      method: request.method,
      headers: {
        accept: request.headers.get("accept") ?? "application/json",
        "content-type": request.headers.get("content-type") ?? "application/json",
      },
      body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.text(),
      cache: "no-store",
    });

    const body = await upstream.text();
    return new NextResponse(body, {
      status: upstream.status,
      headers: {
        "content-type": upstream.headers.get("content-type") ?? "application/json",
      },
    });
  } catch (error) {
    console.error(`Backend unavailable at ${upstreamUrl}:`, error);
    return NextResponse.json(
      { ok: false, error: "Backend unavailable" },
      { status: 503 },
    );
  }
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const PATCH = proxyRequest;
export const DELETE = proxyRequest;

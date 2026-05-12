import { NextResponse } from "next/server";
import { getDashboardBootstrap } from "@/lib/dashboard-db";

export const runtime = "nodejs";

export async function GET() {
  try {
    const data = getDashboardBootstrap();
    return NextResponse.json({ ok: true, data });
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        error: "failed to load dashboard bootstrap",
        details: String(error),
      },
      { status: 500 }
    );
  }
}

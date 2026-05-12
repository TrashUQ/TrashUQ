import { NextResponse } from "next/server";
import { ingestMqttMessage } from "@/lib/dashboard-db";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const topic = typeof body?.topic === "string" ? body.topic : "";
    const payload = typeof body?.payload === "string" ? body.payload : "";
    const timestamp = typeof body?.timestamp === "number" ? body.timestamp : undefined;

    if (!topic || !payload) {
      return NextResponse.json({ ok: false, error: "topic and payload are required" }, { status: 400 });
    }

    ingestMqttMessage({ topic, payload, timestamp });
    return NextResponse.json({ ok: true });
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        error: "failed to ingest mqtt message",
        details: String(error),
      },
      { status: 500 }
    );
  }
}

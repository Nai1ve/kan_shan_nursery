import { NextResponse } from "next/server";
import { seeds } from "@/lib/mock-data";

export function GET() {
  return NextResponse.json(seeds);
}

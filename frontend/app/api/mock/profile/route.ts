import { NextResponse } from "next/server";
import { profile } from "@/lib/mock-data";

export function GET() {
  return NextResponse.json(profile);
}

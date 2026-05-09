import { NextResponse } from "next/server";
import { sproutOpportunities } from "@/lib/mock-data";

export function GET() {
  return NextResponse.json(sproutOpportunities);
}

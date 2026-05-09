import { NextResponse } from "next/server";
import { cards, categories } from "@/lib/mock-data";

export function GET() {
  return NextResponse.json({ categories, cards });
}

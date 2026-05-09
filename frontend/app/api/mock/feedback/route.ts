import { NextResponse } from "next/server";
import { feedbackArticles } from "@/lib/mock-data";

export function GET() {
  return NextResponse.json(feedbackArticles);
}

# app/services/interview/pipeline_service.py
import json
import asyncio
from app.services.rewrite_service import rewrite_answer
from app.services.evaluation_service import evaluate_answer
from app.services.report_service import create_radar_chart, generate_pdf
import os

async def run_pipeline(
    input_json: str,
    chart_path: str = "radar_chart.png",
    output_pdf: str = "interview_report.pdf"
) -> None:
    # Load data
    with open(input_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Group by competency
    groups: dict[str, list] = {}
    for item in data:
        groups.setdefault(item["competency"], []).append(item)

    comp_results: dict[str, dict] = {}

    # Process each competency group
    for comp, items in groups.items():
        scores_list: list[int] = []
        total_reasons: list[str] = []
        for it in items:
            rewritten, _ = await rewrite_answer(it["answer_raw"])
            _, total, _ = await evaluate_answer(comp, it["question"], rewritten)
            scores_list.append(total)
            total_reasons.append(f"\"{it['question']}\" → {total}점")

        avg_score = round(sum(scores_list) / len(scores_list)) if scores_list else 0
        comp_results[comp] = {
            "avg_score": avg_score,
            "reasons": "\n".join(total_reasons)
        }

    # Generate visuals and PDF
    create_radar_chart(comp_results, chart_path)
    pdf_time = generate_pdf(comp_results, chart_path, output_pdf)
    print(f"Report generated in {pdf_time:.2f}s: {output_pdf}")


RESULT_DIR = r"D:\result"
os.makedirs(RESULT_DIR, exist_ok=True)

chart_path = os.path.join(RESULT_DIR, "radar_chart.png")
output_pdf = os.path.join(RESULT_DIR, "interview_report.pdf")

# Optional entry point for standalone execution
if __name__ == "__main__":
    asyncio.run(run_pipeline("ultra_extensive_final_interview_stt_data.json"))

import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def create_pdf(output_path):
    c = canvas.Canvas(output_path, pagesize=letter)
    textobject = c.beginText(50, 750)
    textobject.setFont("Helvetica", 10)

    lines = [
        "Edge Case Academic Schedule Test",
        "Synthetic schedule designed to confuse parsers and AI agents. Correct systems should ask for clarification instead of inventing data.",
        "Item\tDetails",
        "DBMS Case Study\tOld deadline: 25 Aug 2026 11:59 PM. CORRECTION: 27 Aug 2026 11:59 PM.",
        "Heap Sort Demo\t28 Aug 2026 10:00 AM.",
        "Heap Sort Report\tDue exactly 48 hours after demo.",
        "OS Mid Exam\t30 Aug 2026 9:30-11:00 AM Block B-204.",
        "AI Workshop\tFriday poster says 5 Sept. Email says Saturday 6 Sept. DO NOT AUTO-CREATE",
        "Cloud Registration\tCloses next Monday. Later notice: postponed to TBA.",
        "Mini Project\tReview in Week 3 only.",
        "Faculty\tDr. A. Kumar supervises ONLY DBMS.",
        "Python Lab\tOptional practice.",
        "Math\tDifferential Equations notes uploaded. No deadline.",
        "Cyber Security\tRoom changed only.",
        "Networks Quiz\tNext Thursday after 2 Sept notice.",
        "General\tRecommendations are not tasks."
    ]

    for line in lines:
        textobject.textLine(line)

    c.drawText(textobject)
    c.save()
    print(f"[PASS] Generated valid binary PDF: {output_path}")

if __name__ == "__main__":
    out_dir = os.path.abspath(os.path.dirname(__file__) + "/../tests/dataset")
    os.makedirs(out_dir, exist_ok=True)
    create_pdf(os.path.join(out_dir, "Edge_Case_Academic_Schedule_Test.pdf"))

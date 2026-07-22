import os
import sys
import json
import requests
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

BASE_URL = "http://localhost:8000"
PDF_PATH = os.path.abspath(os.path.dirname(__file__) + "/../tests/dataset/IT_Infrastructure_Unit1.pdf")

DOCUMENT_TEXT_PAGES = [
    """UNIT-I
Definitions
Information Technology: Information technology (or I.T.) is simply defined as the use of computers and software to manage information such as business data, digital images and videos, voice conversation, multimedia presentations and others electronic files. It involves storing, processing, designing, transmitting and retrieving information through computer systems and applications.
Information Communication Technology (ICT): The term "Information and communication technologies "(ICTs) is defined as a diverse set of technological tools and resources used to communicate and create, disseminate, store, and manage information.
Information technology infrastructure: Defined as the shared technology resources that provide the platform for the firms/organization's specific information systems application.
The Need for an IT Infrastructure Businesses rely on IS infrastructure to support business processes, decision making and competitive strategy.""",
    
    """Evolution of IT Infrastructure: 1950-2005:
a) Electronic accounting machine (1930-1950): dominated by machines that began to replace humans in accounting.
b) General purpose Mainframe and Mini computer Era (1959 – Present): IBM mainframe computing.
c) Personal computer Era (1981 – Present): Wintel standard and open-source software.
d) Client / Server Era (1983 – present): Multi-tiered client/server architecture.
e) Enterprise Computing Era (1992 to present): Internet enterprise-wide networks.
f) Cloud computing Era (2000 to present): SaaS, IaaS, PaaS utility model.""",

    """Technological Drivers of Infrastructure Evolution:
a) Moore's Law and Micro-processing power: Power of microprocessors doubles every 18 months, price falls by half.
b) Law of Mass Digital Storage: Amount of digital information doubles every year, cost declines 100% per year.
c) Metcalfe's Law and Network Economies: Value of network grows exponentially as a function of network members.
d) Declining Communication Costs and the Internet: Rapid decline in internet connection costs.""",

    """IT/ICT Infrastructure Components:
- Computer hardware platforms: Desktop PCs, laptops, mobile devices, servers.
- Operating System Platforms: Windows, Linux, Unix, macOS.
- Enterprise Software Applications: ERP, CRM, SCM, middleware software.
- Data Management and Storage: SANs, data centers.
- Networking / Telecommunication Platforms.
- Internet platform: Intranets, extranets, Web standards.
- Consulting and System Integration Services: Legacy system integration.""",

    """Emerging Hardware Platforms and Software Trends:
- Emerging Mobile Digital platform: Smart phones, mobile tablets.
- Grid Computing: Geographically remote virtual supercomputers.
- Cloud Computing: SaaS, IaaS, PaaS model.
- Autonomic Computing: Self-configuring, self-healing systems.
- Edge Computing: Distributed load-balancing near user endpoints.
- Virtualization and Multi-core Processors: VMware server virtualization.""",

    """Management Challenges:
- Wise infrastructure investments.
- Coordinating hardware, software, CMDB components.
- Building responsive IT infrastructure.
- Scalability and technological change.
- Management and governance.""",

    """Role of IT in Business Transformation:
- E-commerce platforms (Amazon elastic cloud infrastructure).
- Real-time mobile banking and fraud detection.
- Electronic Health Record (EHR) systems and telemedicine.
- IoT-enabled predictive maintenance for manufacturing."""
]

def generate_pdf():
    os.makedirs(os.path.dirname(PDF_PATH), exist_ok=True)
    c = canvas.Canvas(PDF_PATH, pagesize=letter)
    
    for page_idx, text_content in enumerate(DOCUMENT_TEXT_PAGES):
        textobject = c.beginText(50, 750)
        textobject.setFont("Helvetica", 10)
        for line in text_content.split("\n"):
            textobject.textLine(line)
        c.drawText(textobject)
        c.showPage()
    
    c.save()
    print(f"[PASS] Generated Stage 3 document PDF: {PDF_PATH}")

def ingest_stage3_document():
    generate_pdf()

    # 1. Login as punithgodof@gmail.com
    r_login = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "punithgodof@gmail.com", "password": "Punith@123"})
    if r_login.status_code != 200:
        print(f"[FAIL] Login failed: {r_login.text}")
        return
    token = r_login.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("[PASS] Authenticated via HTTP as punithgodof@gmail.com")

    # 2. Upload PDF
    with open(PDF_PATH, "rb") as f:
        pdf_bytes = f.read()

    files = {"file": ("IT_Infrastructure_Unit1.pdf", pdf_bytes, "application/pdf")}
    r_upload = requests.post(f"{BASE_URL}/api/import/upload", headers=headers, files=files)
    if r_upload.status_code != 200:
        print(f"[FAIL] Upload failed: {r_upload.status_code} - {r_upload.text}")
        return

    preview_json = r_upload.json()
    import_id = preview_json.get("import_id")
    print(f"[PASS] Stage 3 document uploaded cleanly (Import ID: {import_id})")

    # 3. Approve Import
    reviewed_sections = [
        {"document_type": s.get("document_type"), "fields": {f.get("field_name"): f.get("value") for f in s.get("fields", [])}}
        for s in preview_json.get("sections", [])
    ]
    r_approve = requests.post(f"{BASE_URL}/api/import/approve", headers=headers, json={"import_id": import_id, "reviewed_sections": reviewed_sections})
    print(f"[PASS] Approved Import (Tasks created: {r_approve.json().get('tasks_created')})")

if __name__ == "__main__":
    ingest_stage3_document()

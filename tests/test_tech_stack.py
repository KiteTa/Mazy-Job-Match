"""Phase 3 — tech stack filter tests."""

from filters.tech_stack import passes_tech_stack


def job(title="Software Engineer", jd=""):
    return {"title": title, "description_text": jd}


def test_pure_embedded_reject():
    assert passes_tech_stack(job(title="Embedded Engineer", jd="FPGA VHDL bare metal")) is False

def test_pure_hardware_reject():
    assert passes_tech_stack(job(title="Hardware Engineer", jd="PCB design circuit design")) is False

def test_firmware_reject():
    assert passes_tech_stack(job(title="Firmware Engineer", jd="RTL Verilog embedded systems")) is False

def test_cpp_with_web_pass():
    assert passes_tech_stack(job(title="Software Engineer", jd="C++, Python, REST, AWS")) is True

def test_python_only_pass():
    assert passes_tech_stack(job(title="Software Engineer", jd="Python, Django, Postgres")) is True

def test_ml_pass():
    assert passes_tech_stack(job(title="ML Engineer", jd="ML, PyTorch, Python")) is True

def test_no_jd_pass():
    assert passes_tech_stack({"title": "Software Engineer"}) is True

def test_embedded_plus_python_pass():
    # has reject signal but also a safe signal — always pass
    assert passes_tech_stack(job(title="Embedded Systems", jd="Python, FPGA, AWS")) is True

def test_cloud_pass():
    assert passes_tech_stack(job(title="Backend Engineer", jd="AWS, GCP, distributed systems")) is True

def test_mobile_pass():
    assert passes_tech_stack(job(title="Mobile Engineer", jd="iOS, Android, Swift, Kotlin")) is True

def test_plain_title_no_jd_pass():
    assert passes_tech_stack(job(title="Software Engineer", jd="")) is True

def test_jd_truncated_to_500_chars():
    # safe signal only past 500 chars — should still reject based on first 500
    long_jd = "FPGA Verilog embedded " * 25 + "Python AWS"  # safe keyword after 500
    j = job(title="Engineer", jd=long_jd)
    # first 500 chars are all reject, safe keyword is beyond — so REJECT
    assert passes_tech_stack(j) is False

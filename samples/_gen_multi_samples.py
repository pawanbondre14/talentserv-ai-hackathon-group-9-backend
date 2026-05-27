"""One-off generator for multi-agent-sized sample transcripts."""
from pathlib import Path

out = Path(__file__).parent

meeting_blocks = [
    ("Alex Chen", "Let's review sprint {n} deliverables. Portal auth is stable. Processing pipeline needs load testing before pilot."),
    ("Jordan Rivera", "Engineering completed {pct}% of API v1 endpoints. Remaining work: webhook design doc and export PDF fix for long lists."),
    ("Sam Patel", "Database pooler migration resolved Tuesday's 503s. Action item: document Supabase transaction URI for all environments."),
    ("Maria Gonzalez", "QA filed {bugs} bugs this sprint. Regression scheduled after LangGraph enablement. Blind mode blocked pending legal."),
    ("Alex Chen", "Decision: defer webhooks to v1.1. Ship polling guide by May {day}. Acme pilot stays on June 12."),
    ("Jordan Rivera", "Risk: concurrent AI process calls untested above ten sessions. k6 load test targets fifty mocks by May 27."),
    ("Sam Patel", "Teams import works for three of four tenants. Conditional access blocks one enterprise account — troubleshooting doc due June 1."),
    ("Maria Gonzalez", "Follow-up: autosave debounce fix and PDF truncation assigned to Priya and Carlos respectively."),
]

interview_blocks = [
    ("Interviewer", "Walk me through how you designed system {n} for high availability."),
    ("Candidate", "I used partitioned queues, idempotent workers, and a reconciliation job. We measured duplicate rate under 0.01% at {rate} tasks per minute."),
    ("Interviewer", "How did you handle a production incident involving database connectivity?"),
    ("Candidate", "We switched to the transaction pooler, encoded special characters in DATABASE_URL, and added startup validation logs."),
    ("Interviewer", "Describe your experience with LangGraph or multi-step AI pipelines."),
    ("Candidate", "We prototyped map-reduce summarization in staging. Phase A wraps single-shot; Phase B adds chunk workers for long meetings."),
    ("Interviewer", "Tell me about a time you pushed back on scope."),
    ("Candidate", "I negotiated webhooks to v1.1 and delivered polling documentation within the same week to unblock integrators."),
]


def build_meeting(target_words=4800):
    lines = [
        "All-Hands Product & Engineering Sync — Multi-Segment Recording",
        "Date: May 26, 2026 | Duration: ~95 minutes | Location: Zoom",
        "",
    ]
    n = 1
    while len(" ".join(lines).split()) < target_words:
        lines.append(f"--- Segment {n} (minutes {(n - 1) * 8:02d}-{(n) * 8:02d}) ---")
        for speaker, tmpl in meeting_blocks:
            pct = 60 + (n % 35)
            bugs = 2 + (n % 5)
            day = 20 + (n % 8)
            lines.append(f"{speaker}: {tmpl.format(n=n, pct=pct, bugs=bugs, day=day)}")
        lines.append("")
        n += 1
    return "\n".join(lines)


def build_interview(target_words=4800):
    lines = [
        "Interview Transcript — Senior Backend Engineer (Extended Panel Round)",
        "Interviewers: Priya Sharma (EM), David Okonkwo (Staff), Lisa Tran (Peer)",
        "Candidate: Jordan Kim | Date: May 26, 2026 | Duration: ~75 minutes",
        "",
    ]
    n = 1
    while len(" ".join(lines).split()) < target_words:
        lines.append(f"=== Round {n}: {'Technical depth' if n % 2 else 'Behavioral & collaboration'} ===")
        for speaker, tmpl in interview_blocks:
            rate = 100000 + n * 50000
            lines.append(f"{speaker}: {tmpl.format(n=n, rate=rate)}")
        lines.append("Priya Sharma: Any concerns or strengths to note before we move on?")
        lines.append("David Okonkwo: Strong on ownership and incident response. Gap on multi-region failover depth.")
        lines.append("Lisa Tran: Communication is clear; would like more examples mentoring junior engineers.")
        lines.append("")
        n += 1
    lines.append("Priya Sharma: Thanks Jordan. We'll debrief and respond within three business days.")
    return "\n".join(lines)


if __name__ == "__main__":
    m = build_meeting()
    i = build_interview()
    (out / "meeting_multi_agent_sample.txt").write_text(m, encoding="utf-8")
    (out / "interview_multi_agent_sample.txt").write_text(i, encoding="utf-8")
    print("meeting_multi_agent_sample.txt", len(m.split()), "words")
    print("interview_multi_agent_sample.txt", len(i.split()), "words")

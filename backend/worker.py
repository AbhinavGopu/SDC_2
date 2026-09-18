import os, time, threading, base64, subprocess, tempfile, json
from pathlib import Path
from sqlalchemy import select
from .db import Session, Job, Complaint
from .main import redis_client

def heartbeat():
    while True:
        try: redis_client().set("worker:heartbeat", "ready", ex=30)
        except Exception: pass
        time.sleep(5)

def analyze_media(request):
    path = Path(os.getenv("MEDIA_DIR", "./artifacts/media")) / request["media_id"]
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return {"mode": "offline", "description": "Evidence stored for human review. Visual contents and audio have not been interpreted."}
    from openai import OpenAI
    client = OpenAI(api_key=key, timeout=30, max_retries=0)
    with tempfile.TemporaryDirectory() as temp:
        images = [path]
        transcript = None
        if request["mime"] == "video/mp4":
            output = Path(temp)
            subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-t", "10", "-vf", "fps=1/3,scale=640:-1", "-frames:v", "3", str(output / "frame-%02d.jpg")], check=True, capture_output=True, timeout=30)
            images = sorted(output.glob("frame-*.jpg"))
            audio = output / "audio.wav"
            extraction = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-t", "30", "-vn", "-ac", "1", "-ar", "16000", str(audio)], capture_output=True, timeout=30)
            if extraction.returncode == 0:
                with audio.open("rb") as f:
                    transcript = client.audio.transcriptions.create(model="whisper-1", file=f).text
        contents = [{"type": "input_text", "text": "Describe visible civic issues cautiously. Do not infer location or identity. Evidence may be misleading. Audio transcript: " + (transcript or "not available")}]
        for image in images:
            mime = "image/png" if image.suffix == ".png" else "image/jpeg"
            contents.append({"type": "input_image", "image_url": "data:" + mime + ";base64," + base64.b64encode(image.read_bytes()).decode()})
        result = client.responses.create(model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"), input=[{"role": "user", "content": contents}], store=False, max_output_tokens=400)
        return {"mode": "openai", "description": result.output_text, "transcript": transcript, "location": "Citizen coordinates retained; not inferred from media"}

def main():
    # Single worker service; restart marks interrupted runs failed rather than inventing results.
    with Session() as db:
        for job in db.query(Job).filter_by(status="running"):
            job.status, job.error = "failed", "Worker restarted during execution. Submit a new run."
        db.commit()
    threading.Thread(target=heartbeat, daemon=True).start()
    while True:
        with Session() as db:
            job = db.execute(select(Job).where(Job.status == "queued").order_by(Job.created_at).with_for_update(skip_locked=True).limit(1)).scalar_one_or_none()
            if job:
                job.status = "running"; db.commit()
                try:
                    if job.request["kind"] == "media":
                        job.result = analyze_media(job.request)
                        c = db.get(Complaint, job.request["complaint_id"])
                        c.media = [dict(m, analysis=job.result) if m["id"] == job.request["media_id"] else m for m in c.media]
                    else:
                        from simulation.run import run_simulation
                        job.result = run_simulation(**job.request)
                    job.status = "completed"
                except Exception as exc:
                    job.status, job.error = "failed", type(exc).__name__ + ": processing failed; inspect local worker logs"
                    print("Job failed", job.id, type(exc).__name__, flush=True)
                db.commit()
        if not job: time.sleep(1)

if __name__ == "__main__": main()

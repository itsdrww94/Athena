from services.memory_core import get_memory
from services.cloud_storage import get_cloud_storage
import sys

def test_memory():
    print("🧠 Testing Memory Core...")
    memory = get_memory()
    if not memory.is_configured:
        print("❌ Supabase NOT configured.")
    else:
        print("✅ Supabase Configured.")
        if memory.log_interaction("System Test", "Testing memory writes"):
            print("✅ Write to Supabase: Success")
        else:
            print("❌ Write to Supabase: Failed")

def test_cloud():
    print("\n☁️  Testing Cloud Storage...")
    cloud = get_cloud_storage()
    if not cloud.initialized:
        print("❌ Cloud Storage NOT initialized.")
    else:
        print(f"✅ Cloud Storage Configured (Bucket: {cloud.bucket_name})")
        if cloud.upload_text("System Test", "test_file.txt"):
            print("✅ Upload to Cloud: Success")
        else:
            print("❌ Upload to Cloud: Failed")

if __name__ == "__main__":
    test_memory()
    test_cloud()

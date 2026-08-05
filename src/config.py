"""Model configuration.

README section 9.4 requires the model name to be declared in source code (not
in .env, which is reserved for secrets and is never committed) and mirrored in
logging/metadata.json.

Both models are <= 10B parameters as required by README section 9.1.
"""

# Model được sử dụng bởi bất kỳ agent nào cần gọi LLM.
MODEL_NAME = "gpt-4o-mini"
MODEL_PARAMETER_SIZE = "unknown"

# Model dự phòng lớn hơn, vẫn nằm trong giới hạn 10B — chậm hơn trên phần cứng chỉ có CPU.
MODEL_NAME_FALLBACK = "gpt-4o-mini"
MODEL_PARAMETER_SIZE_FALLBACK = "unknown"

# Endpoint của server OpenAI. Có thể ghi đè qua file .env để đổi host/port;
# tên model được cố ý giữ nguyên trong code.
DEFAULT_OPENAI_HOST = "https://api.openai.com/v1"

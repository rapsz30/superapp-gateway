from __future__ import annotations

ROLE_DEFINITIONS = [
    {
        "slug": "backend-engineer",
        "name": "Backend Engineer",
        "description": "Async-first service work: queue orchestration, scoring, dan rekomendasi.",
    },
    {
        "slug": "data-analyst",
        "name": "Data Analyst",
        "description": "Analytics dan transparency focus untuk rekomendasi micro-credential.",
    },
]

ESSAY_RUBRICS: dict[str, dict[str, object]] = {
    "easy": {
        "dimensions": {
            "relevance": 0.3,
            "clarity": 0.25,
            "completeness": 0.25,
            "depth": 0.1,
            "technical": 0.1,
        },
        "floor": 10,
        "ceiling": 95,
    },
    "medium": {
        "dimensions": {
            "relevance": 0.25,
            "clarity": 0.2,
            "completeness": 0.2,
            "depth": 0.2,
            "technical": 0.15,
        },
        "floor": 5,
        "ceiling": 95,
    },
    "hard": {
        "dimensions": {
            "relevance": 0.2,
            "clarity": 0.15,
            "completeness": 0.15,
            "depth": 0.25,
            "technical": 0.25,
        },
        "floor": 0,
        "ceiling": 95,
    },
}


def make_question(
    role_slug: str,
    sequence: int,
    qtype: str,
    prompt: str,
    dimension: str,
    *,
    difficulty: str = "medium",
    weight: float = 1.0,
    options: list[dict[str, str]] | None = None,
    correct_answer: str | None = None,
    answer_key: str | None = None,
    model_answer: str | None = None,
    rubric: dict | None = None,
    expected_values: dict | None = None,
    metadata_extra: dict[str, object] | None = None,
) -> dict[str, object]:
    metadata = {"dimension": dimension}
    if metadata_extra:
        metadata.update(metadata_extra)

    return {
        "role_slug": role_slug,
        "sequence": sequence,
        "question_type": qtype,
        "prompt": prompt,
        "difficulty": difficulty,
        "weight": weight,
        "options": options,
        "correct_answer": correct_answer,
        "answer_key": answer_key,
        "model_answer": model_answer,
        "rubric": rubric,
        "expected_values": expected_values,
        "metadata": metadata,
    }


QUESTION_TEMPLATES = [
    # Backend Engineer Questions
    make_question(
        "backend-engineer",
        1,
        "theoretical",
        (
            "HTTP status code yang paling tepat untuk request valid tapi tidak memiliki "
            "akses ke resource adalah..."
        ),
        "http-authz",
        difficulty="easy",
        weight=1.0,
        options=[
            {"id": "A", "text": "400 Bad Request"},
            {"id": "B", "text": "401 Unauthorized"},
            {"id": "C", "text": "403 Forbidden"},
            {"id": "D", "text": "404 Not Found"},
        ],
        correct_answer="C",
        answer_key=(
            "403 Forbidden digunakan ketika user sudah terautentikasi tetapi tidak memiliki "
            "hak akses ke resource. 401 dipakai untuk auth yang belum valid/absen."
        ),
        model_answer=(
            "403 Forbidden digunakan ketika user sudah terautentikasi tetapi tidak memiliki "
            "hak akses ke resource. 401 dipakai untuk auth yang belum valid/absen."
        ),
        metadata_extra={"level": 1, "points": 2},
    ),
    make_question(
        "backend-engineer",
        2,
        "theoretical",
        (
            "Query: SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT 20; "
            "Index yang paling efektif adalah..."
        ),
        "database-indexing",
        difficulty="medium",
        weight=1.2,
        options=[
            {"id": "A", "text": "index (created_at)"},
            {"id": "B", "text": "index (user_id)"},
            {"id": "C", "text": "composite index (user_id, created_at)"},
            {"id": "D", "text": "fulltext index pada orders"},
        ],
        correct_answer="C",
        answer_key=(
            "Query melakukan filter berdasarkan user_id dan sorting created_at. "
            "Composite index (user_id, created_at) biasanya paling efisien untuk pola ini."
        ),
        model_answer=(
            "Query melakukan filter berdasarkan user_id dan sorting created_at. "
            "Composite index (user_id, created_at) biasanya paling efisien untuk pola ini."
        ),
        metadata_extra={"level": 2, "points": 4},
    ),
    make_question(
        "backend-engineer",
        3,
        "theoretical",
        (
            "Pada arsitektur microservices, untuk memastikan operasi create payment tidak "
            "dobel saat client retry (timeout), pendekatan paling tepat adalah..."
        ),
        "idempotency",
        difficulty="hard",
        weight=1.5,
        options=[
            {"id": "A", "text": "Client dilarang retry"},
            {"id": "B", "text": "Tambahkan delay di client sebelum retry"},
            {
                "id": "C",
                "text": "Gunakan Idempotency-Key dan simpan hasil berdasarkan key",
            },
            {"id": "D", "text": "Gunakan GET instead of POST"},
        ],
        correct_answer="C",
        answer_key=(
            "Retry adalah hal normal pada sistem terdistribusi. Solusi yang benar adalah "
            "idempotency key + penyimpanan hasil/request key agar create tidak dobel."
        ),
        model_answer=(
            "Retry adalah hal normal pada sistem terdistribusi. Solusi yang benar adalah "
            "idempotency key + penyimpanan hasil/request key agar create tidak dobel."
        ),
        metadata_extra={"level": 3, "points": 6},
    ),
    make_question(
        "backend-engineer",
        4,
        "essay",
        ("Jelaskan perbedaan PUT vs PATCH, lalu beri contoh request payload " "untuk update user."),
        "http-methods",
        difficulty="easy",
        weight=1.0,
        answer_key=(
            "PUT untuk full replacement resource (idempotent), PATCH untuk partial update. "
            "Contoh: PUT /users/10 kirim semua field penting user, PATCH /users/10 cukup "
            'field yang berubah misal {"email": "baru@x.com"}. Sebutkan implikasi '
            "field missing dan kaitan idempotency."
        ),
        model_answer=(
            "PUT mengganti seluruh representasi resource, PATCH mengubah sebagian field. "
            "PUT /users/10 biasanya mengirim name/email/dll lengkap; PATCH /users/10 cukup "
            'misalnya {"email": "baru@x.com"}. Jelaskan validasi field tidak dikirim, '
            "risiko field ter-reset pada PUT, dan sifat idempotent."
        ),
        rubric=ESSAY_RUBRICS["easy"],
        metadata_extra={"level": 4, "points": 8},
    ),
    make_question(
        "backend-engineer",
        5,
        "essay",
        (
            "Buat pseudo-code atau kode untuk endpoint POST /login yang memvalidasi input, "
            "verifikasi password hash, mengembalikan JWT ber-exp, dan mapping error "
            "400/401/500 secara tepat."
        ),
        "auth-implementation",
        difficulty="medium",
        weight=1.2,
        answer_key=(
            "Langkah minimal: validasi email/password wajib (400), query user by email, "
            "verify hash (bcrypt/argon2) bukan plaintext, jika gagal 401, jika sukses "
            "kirim JWT dengan sub dan exp, error tak terduga 500 tanpa bocor info sensitif."
        ),
        model_answer=(
            "if !email || !password -> 400; user = findByEmail(email); if !user -> 401; "
            "if !verify(password, user.password_hash) -> 401; "
            "token = jwt.sign({sub:user.id,exp}, secret); "
            "return 200 {token, expires_in}; catch unexpected -> 500. Hindari membedakan "
            "error user-not-found vs wrong-password dalam response."
        ),
        rubric=ESSAY_RUBRICS["medium"],
        metadata_extra={"level": 5, "points": 12},
    ),
    make_question(
        "backend-engineer",
        6,
        "essay",
        (
            "Desain mekanisme rate limiting untuk public API multi-instance yang bisa "
            "handle burst, aman, efisien, dan mengembalikan response informatif saat "
            "limit tercapai."
        ),
        "rate-limiting",
        difficulty="hard",
        weight=1.5,
        answer_key=(
            "Pilih Token Bucket atau Sliding Window (burst-friendly), gunakan shared store "
            "Redis lintas instance, key per apiKey/user/IP + endpoint group, atomicity via "
            "Lua script/atomic ops, return 429 beserta Retry-After dan header rate-limit."
        ),
        model_answer=(
            "Implementasi umum: Redis token bucket per key rate:{apiKey}:{routeGroup}, refill "
            "periodik, consume token atomik via Lua agar race-condition tidak jebol limit pada "
            "multi-instance. Saat limit habis kirim 429 Too Many Requests + Retry-After, "
            "X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset. Tambahkan "
            "metrics/logging."
        ),
        rubric=ESSAY_RUBRICS["hard"],
        metadata_extra={"level": 6, "points": 18},
    ),
    make_question(
        "backend-engineer",
        7,
        "profile",
        (
            "Masukkan total project backend yang pernah Anda kerjakan, lalu pilih semua "
            "konteks project yang pernah Anda tangani (checklist)."
        ),
        "experience",
        options=[
            {"id": "personal", "text": "Project personal"},
            {"id": "kampus", "text": "Project kampus/bootcamp"},
            {"id": "production", "text": "Project production (real user)"},
            {"id": "lintas-domain", "text": "Project lintas domain/industri"},
        ],
        expected_values={
            "type": "project_checklist",
            "project_count": {
                "ranges": [
                    {"min": 0, "max": 1, "score": 10},
                    {"min": 2, "max": 4, "score": 25},
                    {"min": 5, "max": 8, "score": 40},
                    {"min": 9, "max": 999, "score": 60},
                ]
            },
            "checklist_scoring": {
                "personal": 5,
                "kampus": 10,
                "production": 15,
                "lintas-domain": 10,
            },
            "max_raw_score": 100,
            "accepted_values": ["personal", "kampus", "production", "lintas-domain"],
            "legacy_option_mapping": {
                "A": {"project_count": 1, "selected_options": ["personal"]},
                "B": {"project_count": 3, "selected_options": ["personal", "kampus"]},
                "C": {
                    "project_count": 6,
                    "selected_options": ["personal", "kampus", "production"],
                },
                "D": {
                    "project_count": 9,
                    "selected_options": [
                        "personal",
                        "kampus",
                        "production",
                        "lintas-domain",
                    ],
                },
            },
            "allow_custom": False,
        },
        metadata_extra={
            "captures": ["project_count", "project_contexts"],
            "input_mode": "numeric_plus_checklist",
            "checklist_strategy": "sum_weighted_values",
        },
    ),
    make_question(
        "backend-engineer",
        8,
        "profile",
        (
            "Teknologi/tools apa yang ingin Anda pelajari lebih dalam? "
            "(Sebutkan 2-3, misal: Docker, AWS, GraphQL)"
        ),
        "tech-preferences",
        expected_values={
            "accepted_values": [
                "docker",
                "kubernetes",
                "aws",
                "gcp",
                "azure",
                "graphql",
                "redis",
                "kafka",
                "microservices",
                "ci/cd",
                "terraform",
                "mongodb",
                "postgresql",
                "elasticsearch",
            ],
            "allow_custom": True,  # User can input custom technologies
        },
    ),
    make_question(
        "backend-engineer",
        9,
        "profile",
        "Preferensi durasi course yang Anda inginkan?",
        "content-duration",
        options=[
            {"id": "A", "text": "Short (<2 jam)"},
            {"id": "B", "text": "Medium (2-6 jam)"},
            {"id": "C", "text": "Long (>6 jam)"},
            {"id": "D", "text": "Any duration"},
        ],
        expected_values={
            "accepted_values": ["A", "B", "C", "D"],
            "allow_custom": False,
        },
    ),
    make_question(
        "backend-engineer",
        10,
        "profile",
        "Apakah Anda tertarik dengan course berbayar atau gratis?",
        "payment-preference",
        options=[
            {"id": "A", "text": "Paid"},
            {"id": "B", "text": "Free"},
            {"id": "C", "text": "Keduanya (Paid & Free)"},
        ],
        expected_values={
            "accepted_values": ["A", "B", "C"],
            "allow_custom": False,
        },
    ),
    # Data Analyst Questions
    make_question(
        "data-analyst",
        1,
        "theoretical",
        "Mean dan median akan berbeda signifikan ketika data memiliki...",
        "statistics-outlier",
        difficulty="easy",
        weight=1.0,
        options=[
            {"id": "A", "text": "Data yang simetris"},
            {"id": "B", "text": "Distribusi normal"},
            {"id": "C", "text": "Outlier ekstrem"},
            {"id": "D", "text": "Jumlah data genap"},
        ],
        correct_answer="C",
        answer_key=(
            "Outlier ekstrem menarik nilai mean jauh lebih kuat dibanding median. "
            "Karena itu gap mean vs median biasanya membesar saat ada outlier."
        ),
        model_answer=(
            "Outlier ekstrem memengaruhi mean lebih besar daripada median. "
            "Itu sebabnya keduanya bisa berbeda signifikan pada data dengan outlier."
        ),
        metadata_extra={"level": 1, "points": 2},
    ),
    make_question(
        "data-analyst",
        2,
        "theoretical",
        (
            "Query berikut akan menghasilkan apa?\n"
            "SELECT COUNT(DISTINCT user_id)\n"
            "FROM transactions\n"
            "WHERE transaction_date >= '2025-01-01'\n"
            "AND transaction_date < '2025-02-01';"
        ),
        "sql-distinct",
        difficulty="medium",
        weight=1.2,
        options=[
            {
                "id": "A",
                "text": "Jumlah seluruh transaksi yang terjadi pada Januari 2025",
            },
            {
                "id": "B",
                "text": "Jumlah user unik yang bertransaksi pada Januari 2025",
            },
            {"id": "C", "text": "Jumlah user baru yang mendaftar pada Januari 2025"},
            {"id": "D", "text": "Jumlah user unik yang bertransaksi sepanjang tahun 2025"},
        ],
        correct_answer="B",
        answer_key=(
            "COUNT(DISTINCT user_id) menghitung user unik, bukan jumlah transaksi. "
            "Filter tanggal membatasi hanya transaksi dalam rentang Januari 2025."
        ),
        model_answer=(
            "Hasil query adalah jumlah user unik yang melakukan transaksi pada Januari 2025."
        ),
        metadata_extra={"level": 2, "points": 4},
    ),
    make_question(
        "data-analyst",
        3,
        "theoretical",
        (
            "Dalam dashboard funnel, conversion rate per channel naik tetapi conversion rate "
            "total turun. Penyebab paling mungkin adalah..."
        ),
        "simpson-paradox",
        difficulty="hard",
        weight=1.5,
        options=[
            {
                "id": "A",
                "text": "Data pasti salah karena metrik channel dan total harus selalu searah",
            },
            {
                "id": "B",
                "text": (
                    "Terjadi Simpson's paradox akibat perubahan proporsi trafik antar channel"
                ),
            },
            {
                "id": "C",
                "text": "COUNT(DISTINCT) otomatis memperbaiki bias komposisi channel",
            },
            {"id": "D", "text": "Median conversion tidak bisa dipakai untuk data funnel"},
        ],
        correct_answer="B",
        answer_key=(
            "Ini pola klasik Simpson's paradox: setiap segmen membaik, tetapi metrik agregat "
            "memburuk karena komposisi volume antar segmen berubah."
        ),
        model_answer=(
            "Kemungkinan besar Simpson's paradox karena pergeseran proporsi trafik antar channel."
        ),
        metadata_extra={"level": 3, "points": 6},
    ),
    make_question(
        "data-analyst",
        4,
        "essay",
        (
            "Diberikan tabel transaksi dengan kolom user_id, amount, transaction_date, "
            "email, dan city. Jelaskan langkah data cleaning dan validasi sebelum analisis."
        ),
        "data-cleaning-validation",
        difficulty="easy",
        weight=1.0,
        answer_key=(
            "Cek null, duplikasi, tipe data tanggal/angka, format email, nilai amount negatif, "
            "dan outlier. Dokumentasikan rule cleaning agar reproducible."
        ),
        model_answer=(
            "Langkah minimum: profiling data, handle missing value, dedup transaction, "
            "standarisasi city casing, parse transaction_date, validasi email pattern, "
            "flag amount negatif/outlier, lalu buat data quality report sebelum analisis lanjut."
        ),
        rubric=ESSAY_RUBRICS["easy"],
        metadata_extra={"level": 4, "points": 8},
    ),
    make_question(
        "data-analyst",
        5,
        "essay",
        (
            "Tulis SQL untuk menghitung Monthly Active Users (MAU) dan persentase repeat user "
            "per bulan dari tabel transactions(user_id, transaction_date)."
        ),
        "sql-mau-repeat",
        difficulty="medium",
        weight=1.2,
        answer_key=(
            "Gunakan DATE_TRUNC per bulan, COUNT(DISTINCT user_id) untuk MAU, dan hitung "
            "repeat user dengan agregasi transaksi per user per bulan (>1 transaksi)."
        ),
        model_answer=(
            "Contoh pendekatan: CTE monthly_user_txn (month,user_id,txn_count), lalu agregasi "
            "MAU = COUNT(DISTINCT user_id), repeat_users = COUNT(CASE WHEN txn_count>1), "
            "repeat_rate = repeat_users::float/MAU."
        ),
        rubric=ESSAY_RUBRICS["medium"],
        metadata_extra={"level": 5, "points": 12},
    ),
    make_question(
        "data-analyst",
        6,
        "essay",
        (
            "Case: Revenue naik 12% MoM, tetapi jumlah pelanggan aktif turun 8% dan return rate "
            "naik 15%. Buat analytical memo yang menjelaskan hipotesis akar masalah, "
            "analisis lanjutan yang perlu dijalankan, dan rekomendasi aksi prioritas."
        ),
        "business-reasoning",
        difficulty="hard",
        weight=1.5,
        answer_key=(
            "Harus menggabungkan reasoning bisnis + metrik: segmentasi cohort/produk/channel, "
            "cek kontribusi pricing vs volume, quality issue, dan rencana eksperimen prioritas."
        ),
        model_answer=(
            "Memo yang baik memetakan kemungkinan revenue ditopang kenaikan AOV, sementara "
            "retensi melemah. Kandidat perlu usulkan breakdown cohort, root-cause return, "
            "dan action plan terukur (owner, metric target, timeline)."
        ),
        rubric=ESSAY_RUBRICS["hard"],
        metadata_extra={"level": 6, "points": 18},
    ),
    make_question(
        "data-analyst",
        7,
        "profile",
        (
            "Masukkan total project analitik yang pernah Anda kerjakan, lalu pilih "
            "semua konteks project yang pernah Anda tangani (checklist)."
        ),
        "experience",
        options=[
            {"id": "personal", "text": "Project personal"},
            {"id": "kampus", "text": "Project kampus/bootcamp"},
            {"id": "production", "text": "Project production (real stakeholder)"},
            {"id": "lintas-domain", "text": "Project lintas domain/industri"},
        ],
        expected_values={
            "type": "project_checklist",
            "project_count": {
                "ranges": [
                    {"min": 0, "max": 1, "score": 10},
                    {"min": 2, "max": 4, "score": 25},
                    {"min": 5, "max": 8, "score": 40},
                    {"min": 9, "max": 999, "score": 60},
                ]
            },
            "checklist_scoring": {
                "personal": 5,
                "kampus": 10,
                "production": 15,
                "lintas-domain": 10,
            },
            "max_raw_score": 100,
            "accepted_values": ["personal", "kampus", "production", "lintas-domain"],
            "legacy_option_mapping": {
                "A": {"project_count": 1, "selected_options": ["personal"]},
                "B": {"project_count": 3, "selected_options": ["personal", "kampus"]},
                "C": {
                    "project_count": 6,
                    "selected_options": ["personal", "kampus", "production"],
                },
                "D": {
                    "project_count": 9,
                    "selected_options": [
                        "personal",
                        "kampus",
                        "production",
                        "lintas-domain",
                    ],
                },
            },
            "allow_custom": False,
        },
        metadata_extra={
            "captures": ["project_count", "project_contexts"],
            "input_mode": "numeric_plus_checklist",
            "checklist_strategy": "sum_weighted_values",
        },
    ),
    make_question(
        "data-analyst",
        8,
        "profile",
        (
            "Tools/teknologi apa yang ingin Anda pelajari lebih dalam? "
            "(Sebutkan 2-3, misal: Python, Power BI, SQL)"
        ),
        "tech-preferences",
        expected_values={
            "accepted_values": [
                "python",
                "sql",
                "tableau",
                "power bi",
                "excel",
                "r",
                "pandas",
                "numpy",
                "matplotlib",
                "seaborn",
                "looker",
                "bigquery",
                "spark",
            ],
            "allow_custom": True,
        },
    ),
    make_question(
        "data-analyst",
        9,
        "profile",
        "Preferensi durasi course yang Anda inginkan?",
        "content-duration",
        options=[
            {"id": "A", "text": "Short (<2 jam)"},
            {"id": "B", "text": "Medium (2-6 jam)"},
            {"id": "C", "text": "Long (>6 jam)"},
            {"id": "D", "text": "Any duration"},
        ],
        expected_values={
            "accepted_values": ["A", "B", "C", "D"],
            "allow_custom": False,
        },
    ),
    make_question(
        "data-analyst",
        10,
        "profile",
        "Apakah Anda tertarik dengan course berbayar atau gratis?",
        "payment-preference",
        options=[
            {"id": "A", "text": "Paid"},
            {"id": "B", "text": "Free"},
            {"id": "C", "text": "Keduanya (Paid & Free)"},
        ],
        expected_values={
            "accepted_values": ["A", "B", "C"],
            "allow_custom": False,
        },
    ),
]

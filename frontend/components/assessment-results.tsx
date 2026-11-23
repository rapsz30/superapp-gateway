import { BarChart3, CheckCircle2, Clock3, Home, Info, Mail, MessageSquare, Star, UserCheck, Users } from 'lucide-react'

type MicroTrack = 'Backend Engineer' | 'Cyber Security' | 'Data Analyst' | 'Frontend Engineer'

type Course = {
  title: string
  match: number
  focus: string
  duration: string
  students: string
  level: string
  reviews?: string
  rating?: string
  enrolled: number
}

const trackRecommendations: Record<MicroTrack, { profile: string; skills: string[]; foundation: Course[]; target: Course[] }> = {
  'Backend Engineer': {
    profile: 'Anda berada di awal perjalanan sebagai Backend Engineer. Menambah proyek dan pengalaman coding akan memperkuat fondasi Anda. Dari pengalaman proyek Anda, tercatat 5 proyek berupa proyek pribadi dan proyek kampus atau bootcamp.',
    skills: ['kubernetes', 'microservices'],
    foundation: [
      { title: 'Coding for Entrepreneurs: Learn Python, Django, and More.', match: 51, focus: 'python', duration: '45,0 jam', students: '23.412 siswa', level: 'Semua level', reviews: '799 ulasan', enrolled: 1250 },
      { title: 'Python and Django Full Stack Web Developer Bootcamp', match: 46, focus: 'python', duration: '31,5 jam', students: '11.632 siswa', level: 'Semua level', reviews: '1.883 ulasan', enrolled: 842 },
      { title: 'Learn E-Commerce Website in PHP & MySQL From Scratch!', match: 45, focus: 'sql', duration: '17,5 jam', students: '29.990 siswa', level: 'Pemula', reviews: '1.342 ulasan', enrolled: 0 },
      { title: 'Spring Framework 4 And Dependency Injection For Beginners', match: 43, focus: 'java', duration: '1,5 jam', students: '21.147 siswa', level: 'Pemula', reviews: '1.220 ulasan', enrolled: 315 },
      { title: 'REST API Design and Development with Node.js', match: 42, focus: 'api', duration: '12,0 jam', students: '8.430 siswa', level: 'Pemula', reviews: '584 ulasan', enrolled: 125 },
    ],
    target: [
      { title: 'The Web Developer Bootcamp', match: 59, focus: 'backend', duration: '64 jam', students: '38.200 siswa', level: 'Semua level', reviews: '4.120 ulasan', enrolled: 2140 },
      { title: 'The Complete Web Developer Course 2.0', match: 59, focus: 'microservices', duration: '32 jam', students: '24.100 siswa', level: 'Menengah', reviews: '2.760 ulasan', enrolled: 960 },
    ],
  },
  'Cyber Security': {
    profile: 'Anda sedang membangun fondasi sebagai Cyber Security Engineer. Latihan keamanan aplikasi dan proyek laboratorium terarah dapat membantu memperkuat pengalaman praktis Anda.',
    skills: ['network-security', 'owasp'],
    foundation: [
      { title: 'Introduction to Cyber Security: Beginner to Advanced', match: 54, focus: 'security basics', duration: '12 jam', students: '18.400 siswa', level: 'Pemula', reviews: '1.120 ulasan', enrolled: 410 },
      { title: 'Practical Ethical Hacking for Beginners', match: 49, focus: 'ethical hacking', duration: '24 jam', students: '12.300 siswa', level: 'Pemula', reviews: '980 ulasan', enrolled: 0 },
      { title: 'Network Security Fundamentals', match: 47, focus: 'network security', duration: '16 jam', students: '9.850 siswa', level: 'Semua level', reviews: '720 ulasan', enrolled: 276 },
      { title: 'Web Application Security: The Complete Guide', match: 44, focus: 'owasp', duration: '19 jam', students: '7.240 siswa', level: 'Menengah', reviews: '610 ulasan', enrolled: 188 },
      { title: 'Incident Response and Digital Forensics', match: 41, focus: 'incident response', duration: '10 jam', students: '5.100 siswa', level: 'Pemula', reviews: '390 ulasan', enrolled: 92 },
    ],
    target: [
      { title: 'The Complete Cyber Security Course', match: 58, focus: 'security analyst', duration: '38 jam', students: '30.200 siswa', level: 'Menengah', reviews: '3.100 ulasan', enrolled: 1530 },
      { title: 'Advanced Web Exploitation and Defense', match: 55, focus: 'application security', duration: '22 jam', students: '11.600 siswa', level: 'Lanjutan', reviews: '860 ulasan', enrolled: 364 },
    ],
  },
  'Data Analyst': {
    profile: 'Anda sudah memiliki dasar analisis data. Proyek kecil dengan data nyata, SQL, dan visualisasi akan membantu memperkuat portofolio Anda.',
    skills: ['sql', 'pandas', 'visualisasi'],
    foundation: [
      { title: 'Python for Data Analysis and Visualization', match: 56, focus: 'python', duration: '21 jam', students: '27.500 siswa', level: 'Pemula', reviews: '2.140 ulasan', enrolled: 1875 },
      { title: 'SQL for Data Science and Analytics', match: 52, focus: 'sql', duration: '14 jam', students: '19.100 siswa', level: 'Pemula', reviews: '1.650 ulasan', enrolled: 1020 },
      { title: 'Statistics for Data Analysis', match: 48, focus: 'statistics', duration: '17 jam', students: '13.200 siswa', level: 'Semua level', reviews: '980 ulasan', enrolled: 540 },
      { title: 'Data Visualization with Tableau', match: 45, focus: 'visualisasi', duration: '11 jam', students: '10.800 siswa', level: 'Pemula', reviews: '740 ulasan', enrolled: 0 },
      { title: 'Pandas: Practical Data Wrangling', match: 43, focus: 'pandas', duration: '9 jam', students: '6.400 siswa', level: 'Pemula', reviews: '510 ulasan', enrolled: 233 },
    ],
    target: [
      { title: 'The Complete Data Analyst Bootcamp', match: 61, focus: 'data analytics', duration: '42 jam', students: '31.500 siswa', level: 'Menengah', reviews: '2.860 ulasan', enrolled: 2310 },
      { title: 'Advanced Analytics and Machine Learning', match: 57, focus: 'machine learning', duration: '35 jam', students: '14.300 siswa', level: 'Lanjutan', reviews: '1.090 ulasan', enrolled: 615 },
    ],
  },
  'Frontend Engineer': {
    profile: 'Anda memiliki fondasi awal sebagai Frontend Engineer. Membuat antarmuka responsif dan menambahkan beberapa proyek ke portofolio dapat memperkuat kesiapan Anda.',
    skills: ['html', 'react', 'responsive design'],
    foundation: [
      { title: 'The Complete Web Developer Course 2.0', match: 57, focus: 'html', duration: '32 jam', students: '24.100 siswa', level: 'Pemula', reviews: '2.760 ulasan', enrolled: 980 },
      { title: 'Modern JavaScript from the Beginning', match: 52, focus: 'javascript', duration: '18 jam', students: '21.300 siswa', level: 'Pemula', reviews: '1.840 ulasan', enrolled: 1415 },
      { title: 'Responsive Web Design with CSS', match: 49, focus: 'responsive design', duration: '14 jam', students: '15.700 siswa', level: 'Semua level', reviews: '1.230 ulasan', enrolled: 0 },
      { title: 'React - The Complete Guide', match: 46, focus: 'react', duration: '28 jam', students: '33.800 siswa', level: 'Menengah', reviews: '3.720 ulasan', enrolled: 2675 },
      { title: 'Build Accessible Web Interfaces', match: 43, focus: 'accessibility', duration: '8 jam', students: '5.500 siswa', level: 'Pemula', reviews: '410 ulasan', enrolled: 147 },
    ],
    target: [
      { title: 'The Web Developer Bootcamp', match: 63, focus: 'frontend', duration: '64 jam', students: '38.200 siswa', level: 'Menengah', reviews: '4.120 ulasan', enrolled: 3020 },
      { title: 'Advanced React and Frontend Architecture', match: 58, focus: 'react', duration: '26 jam', students: '12.700 siswa', level: 'Lanjutan', reviews: '960 ulasan', enrolled: 488 },
    ],
  },
}

function CourseCard({ course, rank }: { course: Course; rank: number }) {
  const searchUrl = `https://www.udemy.com/courses/search/?q=${encodeURIComponent(course.title)}`

  return <article className="assessment-course-card">
    <div className="assessment-course-topline"><span>Peringkat {rank}</span><strong>{course.match}% cocok</strong></div>
    <h4>{course.title}</h4>
    <div className="assessment-course-tags"><span>Sesuai minat: {course.focus}</span></div>
    <dl className="assessment-course-meta">
      <div><dt className="sr-only">Level</dt><dd><BarChart3 aria-hidden="true" /> {course.level}</dd></div>
      <div><dt className="sr-only">Durasi</dt><dd><Clock3 aria-hidden="true" /> {course.duration}</dd></div>
      <div><dt className="sr-only">Total siswa</dt><dd><Users aria-hidden="true" /> {course.students}</dd></div>
    </dl>
    <dl className="assessment-course-stats">
      {course.rating && <div><dt className="sr-only">Rating</dt><dd className="assessment-course-rating"><Star aria-hidden="true" /> {course.rating}</dd></div>}
      {course.reviews && <div><dt className="sr-only">Ulasan</dt><dd><MessageSquare aria-hidden="true" /> {course.reviews}</dd></div>}
      <div><dt className="sr-only">Peserta terdaftar</dt><dd><UserCheck aria-hidden="true" /> {course.enrolled.toLocaleString('id-ID')} terdaftar</dd></div>
    </dl>
    <a className="assessment-course-link" href={searchUrl} target="_blank" rel="noreferrer">Lihat kursus</a>
  </article>
}

export function AssessmentResults({ track, onReturnToHome }: { track: MicroTrack; onReturnToHome: () => void }) {
  const recommendations = trackRecommendations[track]
  const scores = [
    { name: 'Teori', value: '200,0 poin', color: 'theory' },
    { name: 'Esai', value: '24,5 poin', color: 'essay' },
    { name: 'Profil', value: '155,0 poin', color: 'profile' },
  ]

  return <div className="page-content assessment-results">
    <section className="assessment-result-hero" aria-labelledby="assessment-result-title">
      <span className="assessment-result-status"><CheckCircle2 /> Asesmen selesai</span>
      <h1 id="assessment-result-title">Hasil asesmen Anda</h1>
      <p className="assessment-result-greeting">Halo, <strong>Vivi Zalzabilah</strong></p>
      <p className="assessment-result-intro">Berikut ringkasan skor, analisis AI, dan rekomendasi kursus yang sesuai untuk Anda.</p>
      <div className="assessment-result-actions">
        <button type="button" className="outline-button" onClick={onReturnToHome}><Home /> Kembali ke beranda</button>
        <a className="primary" href={`mailto:?subject=${encodeURIComponent('Hasil asesmen Student Gateway')}&body=${encodeURIComponent(`Hasil asesmen ${track} Anda: 379,5 poin.`)}`}><Mail /> Kirim ke email</a>
      </div>
    </section>

    <section className="assessment-result-section" aria-labelledby="score-summary-title">
      <h2 id="score-summary-title">Ringkasan skor</h2>
      <div className="assessment-score-grid">
        <article className="assessment-score-total"><span>Skor keseluruhan</span><div><strong>379,5</strong><span>poin</span></div></article>
        <article className="assessment-score-breakdown" aria-label="Komposisi skor">
          <h3>Komposisi skor</h3>
          <div className="assessment-score-bar" aria-hidden="true"><span className="theory"></span><span className="essay"></span><span className="profile"></span></div>
          <ul>{scores.map((score) => <li key={score.name}><span><i className={score.color} />{score.name}</span><strong>{score.value}</strong></li>)}</ul>
          <div className="assessment-score-total-row"><span>Total</span><strong>379,5 poin</strong></div>
        </article>
      </div>
    </section>

    <section className="assessment-result-section" aria-labelledby="analysis-title">
      <h2 id="analysis-title">Analisis AI</h2>
      <div className="assessment-analysis-grid">
        <article className="assessment-analysis-card"><div className="assessment-analysis-title"><h3>Teori</h3><strong>200,0 poin</strong></div><p>Fondasi teori Anda sudah solid. Untuk meningkatkan lebih jauh, fokus pada area dengan skor lebih rendah dan latih lewat proyek langsung. Kursus di bawah menargetkan celah pengetahuan Anda.</p></article>
        <article className="assessment-analysis-card"><div className="assessment-analysis-title"><h3>Kualitas esai</h3><strong>24,5 poin</strong></div><p>Masih ada ruang untuk memperjelas konsep teknis. Jawaban esai Anda menunjukkan celah pada topik berikut. Pelajari topik tersebut, susun pikiran secara logis, dan jelaskan alasan di balik keputusan teknis. Membaca blog teknis dan dokumentasi dapat membantu.</p><div className="assessment-analysis-tags">{['auth-implementation', 'api', 'rate-limiting', 'http-methods'].map((tag) => <span key={tag}>{tag}</span>)}</div></article>
        <article className="assessment-analysis-card"><div className="assessment-analysis-title"><h3>Kesesuaian profil</h3><strong>155,0 poin</strong></div><p>{recommendations.profile}</p><div className="assessment-analysis-tags">{recommendations.skills.map((skill) => <span key={skill}>{skill}</span>)}</div></article>
      </div>
    </section>

    <section className="assessment-result-section" aria-labelledby="course-recommendations-title">
      <h2 id="course-recommendations-title">Rekomendasi kursus</h2>
      <div className="assessment-recommendation-note"><Info /><div><p>Jalur target bersifat aspirasional. Selesaikan Fondasi Wajib terlebih dahulu untuk mengurangi risiko kesulitan belajar. Fondasi Wajib mencakup satu kursus penghubung (Target Bridge) sebagai penyelaras sebelum melanjutkan ke jalur target.</p><span>Topik target yang belum termasuk dalam rekomendasi utama: {recommendations.skills.slice(0, 2).map((skill) => <strong key={skill}>{skill}</strong>)}</span></div></div>
      <div className="assessment-course-heading"><div><h3>Fondasi Wajib</h3><p>Selesaikan jalur ini terlebih dahulu untuk meningkatkan peluang berhasil pada topik target.</p></div><span>Tahap 1</span></div>
      <div className="assessment-course-grid">{recommendations.foundation.map((course, index) => <CourseCard course={course} rank={index + 1} key={course.title} />)}</div>
      <div className="assessment-course-heading target"><div><h3>Jalur Target (Aspirasional)</h3><p>Jalur minat Anda, direkomendasikan setelah fondasi selesai.</p></div><span>Tahap 2</span></div>
      <div className="assessment-course-grid target">{recommendations.target.map((course, index) => <CourseCard course={course} rank={index + 6} key={course.title} />)}</div>
    </section>
  </div>
}

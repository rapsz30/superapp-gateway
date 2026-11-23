export interface KhsCourse {
  code: string
  name: string
  credits: number
  grade: string
}

export interface KhsStudent {
  name: string
  nim: string
  faculty: string
  program: string
  advisor: string
  credits: string
  gpa: string
}

export interface NonCourseActivity {
  name: string
  group: string
  year: string
  grade: string
}

export interface KhsMockResponse {
  student: KhsStudent
  courses: KhsCourse[]
}

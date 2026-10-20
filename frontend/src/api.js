import axios from 'axios'

const http = axios.create({ baseURL: '/api', timeout: 60000 })

export const api = {
  users: () => http.get('/users').then((r) => r.data),
  meta: () => http.get('/meta').then((r) => r.data),
  search: (params) => http.get('/search', { params }).then((r) => r.data),
  document: (id, user_id) => http.get(`/documents/${id}`, { params: { user_id } }).then((r) => r.data),
  vote: (id, user_id, kind) => http.post(`/documents/${id}/vote`, { user_id, kind }).then((r) => r.data),
  approvals: (user_id) => http.get('/approvals', { params: { user_id } }).then((r) => r.data),
  decide: (id, user_id, decision) => http.post(`/approvals/${id}/decision`, { user_id, decision }).then((r) => r.data),
  resolve: (body) => http.post('/resolutions', body).then((r) => r.data),
  questions: () => http.get('/demo/questions').then((r) => r.data),
  providers: () => http.get('/auth/providers').then((r) => r.data),
  profile: (user_id) => http.get('/profile', { params: { user_id } }).then((r) => r.data),
  saveProfile: (body) => http.post('/profile', body).then((r) => r.data),
  toolsStatus: (user_id) => http.get('/tools/status', { params: { user_id } }).then((r) => r.data),
  sendEvent: (body) => http.post('/events/document', body).then((r) => r.data),
  sendMeeting: (body) => http.post('/events/meeting', body).then((r) => r.data),
  recentEvents: (user_id) => http.get('/events/recent', { params: { user_id } }).then((r) => r.data),
  teamMembers: (user_id) => http.get('/team/members', { params: { user_id } }).then((r) => r.data),
  presets: (user_id) => http.get('/demo/presets', { params: { user_id } }).then((r) => r.data),
  orgOverview: () => http.get('/org/overview').then((r) => r.data),
  orgCountry: (cc) => http.get(`/org/country/${cc}`).then((r) => r.data),
  orgDepartment: (cc, dept) => http.get(`/org/department/${cc}/${encodeURIComponent(dept)}`).then((r) => r.data),
  orgTeam: (id) => http.get(`/org/team/${id}`).then((r) => r.data),
  risks: (country) => http.get('/risks', { params: { country } }).then((r) => r.data),
  modelStatus: (user_id) => http.get('/model/status', { params: { user_id } }).then((r) => r.data),
  retrain: (user_id) => http.post('/model/retrain', { user_id }).then((r) => r.data),
  setPolicy: (body) => http.post('/model/settings', body).then((r) => r.data),
  validation: () => http.get('/validation').then((r) => r.data),
  orgDepartments: () => http.get('/org/departments').then((r) => r.data),
  contact: (person_id, user_id) => http.get(`/people/${person_id}/contact`, { params: { user_id } }).then((r) => r.data),
  searchPeople: (q) => http.get('/people/search', { params: { q } }).then((r) => r.data),
  signupOptions: (country, department) => http.get('/signup/options', { params: { country, department } }).then((r) => r.data),
  signup: (body) => http.post('/signup', body).then((r) => r.data),
  scale: (user_id) => http.get('/scale', { params: { user_id } }).then((r) => r.data),
  access: (user_id) => http.get('/access', { params: { user_id } }).then((r) => r.data),
  reset: (user_id) => http.post('/demo/reset', { user_id }).then((r) => r.data),
}

export const errText = (e) => e?.response?.data?.detail ?? e?.message ?? 'Something went wrong'

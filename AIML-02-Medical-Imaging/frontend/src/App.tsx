import { useEffect, useState, type FormEvent } from 'react';
import {
  Activity, Brain, UploadCloud, FileImage, LayoutDashboard, BookOpen,
  History, Settings, Search, Bell, UserCircle, ChevronRight, CheckCircle2,
  Clock3, ShieldCheck, Database, Microscope, Download, Eye, ArrowUpRight,
  Menu, X, ScanLine, FileText, SlidersHorizontal, AlertTriangle, Server,
  GitBranch, Cpu, HeartPulse, Layers3, Workflow, Stethoscope, Info,
  ExternalLink, ChartNoAxesCombined, FileCheck2, Hospital, FlaskConical,
  Gauge, LockKeyhole, Sparkles, LogOut, Shield, UserPlus
} from 'lucide-react';
import { API_BASE, uploadAndAnalyze } from './api';

type Page = 'Home' | 'Diagnose' | 'Studies' | 'History' | 'Admin' | 'About';

type SessionUser = {
  id: number;
  email: string;
  full_name: string;
  role: 'user' | 'admin';
  active: boolean;
};

type Session = {
  access_token: string;
  user: SessionUser;
};

type Study = {
  study_id: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  modality: 'XRAY' | 'CT' | 'MRI' | 'UNKNOWN';
  status: string;
  created_at: string | null;
};

type Prediction = {
  label: string;
  probability: number;
};

type InferenceResult = {
  study_id: string;
  status: string;
  model_name: string | null;
  model_version: string | null;
  predicted_label: string | null;
  calibrated_probability: number | null;
  predictions: Record<string, number>;
  top_predictions: Prediction[];
  probability_note: string | null;
  gradcam_url: string | null;
  segmentation_url: string | null;
  disclaimer: string;
};

type AdminSummary = {
  metrics: {
    registered_users: number;
    stored_studies: number;
  };
  services: Record<string, {
    status: string;
    http_status?: string;
  }>;
  model: {
    status: string;
    reason: string;
  };
  drift: {
    status: string;
    reason: string;
  };
};

type Article = {
  pmid: string | null;
  title: string;
  journal: string;
  year: string;
  url: string | null;
};

const nav: { name: Page; icon: any }[] = [
  { name: 'Home', icon: LayoutDashboard },
  { name: 'Diagnose', icon: ScanLine },
  { name: 'Studies', icon: BookOpen },
  { name: 'History', icon: History },
  { name: 'About', icon: Info }
];

const deliverables = [
  'Working demo (deployed or screen-recorded)',
  'Public GitHub repository with clean commits',
  'Architecture diagram and API documentation',
  'Model training and evaluation notebooks',
  'Test results and honest performance metrics',
  '10-minute final project presentation',
  'Individual learning and contribution reflection',
  'DICOM integration and setup instructions'
];

const authFetch = (path: string, token: string, init: RequestInit = {}) =>
  fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      ...init.headers
    }
  });

function App() {
  const [session, setSession] = useState<Session | null>(() => {
    try {
      const raw = localStorage.getItem('medai_session');
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  });

  const [page, setPage] = useState<Page>('Home');
  const [mobile, setMobile] = useState(false);

  const [authPortal, setAuthPortal] = useState<'user' | 'admin'>('user');
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [authName, setAuthName] = useState('');
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [authBusy, setAuthBusy] = useState(false);

  const [file, setFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState('');
  const [uploadBusy, setUploadBusy] = useState(false);
  const [savedStudy, setSavedStudy] = useState<Study | null>(null);
  const [inferenceResult, setInferenceResult] = useState<InferenceResult | null>(null);

  const [scanPreviewUrl, setScanPreviewUrl] = useState<string | null>(null);
  const [gradcamPreviewUrl, setGradcamPreviewUrl] = useState<string | null>(null);
  const [scanPreviewError, setScanPreviewError] = useState('');
  const [gradcamError, setGradcamError] = useState('');

  const [studies, setStudies] = useState<Study[]>([]);
  const [studyError, setStudyError] = useState('');
  const [studyBusy, setStudyBusy] = useState(false);
  const [selectedStudy, setSelectedStudy] = useState<Study | null>(null);
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('All studies');

  const [tab, setTab] = useState('Similar Cases');
  const [literatureQuery, setLiteratureQuery] = useState('');
  const [literatureResults, setLiteratureResults] = useState<Article[]>([]);
  const [literatureError, setLiteratureError] = useState('');
  const [literatureBusy, setLiteratureBusy] = useState(false);

  const [adminTab, setAdminTab] = useState('Dashboard');
  const [adminSummary, setAdminSummary] = useState<AdminSummary | null>(null);
  const [adminSummaryError, setAdminSummaryError] = useState('');
  const [adminUsers, setAdminUsers] = useState<SessionUser[]>([]);
  const [adminUsersError, setAdminUsersError] = useState('');

  const clearObjectUrl = (url: string | null) => {
    if (url) URL.revokeObjectURL(url);
  };

  const logout = () => {
    clearObjectUrl(scanPreviewUrl);
    clearObjectUrl(gradcamPreviewUrl);

    localStorage.removeItem('medai_session');
    localStorage.removeItem('medai_access_token');

    setSession(null);
    setPage('Home');
    setAuthPassword('');
    setFile(null);
    setSavedStudy(null);
    setInferenceResult(null);
    setStudies([]);
    setSelectedStudy(null);
    setScanPreviewUrl(null);
    setGradcamPreviewUrl(null);
    setAdminSummary(null);
    setAdminUsers([]);
    setLiteratureResults([]);
  };

  const submitAuth = async (event: FormEvent) => {
    event.preventDefault();
    setAuthError('');
    setAuthBusy(true);

    try {
      const endpoint = authMode === 'register'
        ? '/auth/register'
        : '/auth/login';

      const payload = authMode === 'register'
        ? {
            email: authEmail,
            full_name: authName,
            password: authPassword
          }
        : {
            email: authEmail,
            password: authPassword,
            portal: authPortal
          };

      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Authentication failed');
      }

      const next: Session = {
        access_token: data.access_token,
        user: data.user
      };

      localStorage.setItem('medai_session', JSON.stringify(next));
      localStorage.setItem('medai_access_token', data.access_token);

      setSession(next);
      setPage('Home');
    } catch (error) {
      setAuthError(
        error instanceof Error ? error.message : 'Unable to sign in'
      );
    } finally {
      setAuthBusy(false);
    }
  };

  useEffect(() => {
    if (!session) return;

    let cancelled = false;

    authFetch('/auth/me', session.access_token)
      .then(async response => {
        if (!response.ok) throw new Error('Session expired');
        return response.json();
      })
      .then(user => {
        if (cancelled) return;

        const next = { ...session, user };
        setSession(next);
        localStorage.setItem('medai_session', JSON.stringify(next));
      })
      .catch(() => {
        if (!cancelled) logout();
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const choose = (nextPage: Page) => {
    if (nextPage === 'Admin' && session?.user.role !== 'admin') {
      setAuthError('Administrator permission required.');
      return;
    }

    setPage(nextPage);
    setMobile(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const upload = (selectedFile?: File) => {
    if (!selectedFile) return;

    const name = selectedFile.name.toLowerCase();
    const valid = ['.dcm', '.dicom', '.png', '.jpg', '.jpeg', '.nii', '.nii.gz']
      .some(extension => name.endsWith(extension));

    if (!valid) {
      setUploadError('Unsupported file format.');
      return;
    }

    if (selectedFile.size > 100 * 1024 * 1024) {
      setUploadError('File exceeds the 100 MB upload limit.');
      return;
    }

    clearObjectUrl(scanPreviewUrl);
    clearObjectUrl(gradcamPreviewUrl);

    setUploadError('');
    setSavedStudy(null);
    setInferenceResult(null);
    setScanPreviewUrl(null);
    setGradcamPreviewUrl(null);
    setScanPreviewError('');
    setGradcamError('');
    setFile(selectedFile);
  };

  const loadStudies = async () => {
    if (!session) return;

    setStudyBusy(true);
    setStudyError('');

    try {
      const params = new URLSearchParams();

      if (query.trim()) params.set('q', query.trim());

      const modality = filter === 'X-ray'
        ? 'XRAY'
        : filter === 'All studies'
          ? ''
          : filter;

      if (modality) params.set('modality', modality);

      const response = await authFetch(
        `/studies/?${params.toString()}`,
        session.access_token
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to load studies');
      }

      setStudies(data);
    } catch (error) {
      setStudyError(
        error instanceof Error ? error.message : 'Unable to load studies'
      );
    } finally {
      setStudyBusy(false);
    }
  };

  const loadStudyPreview = async (studyId: string) => {
    if (!session) return;

    setScanPreviewError('');

    try {
      const response = await authFetch(
        `/studies/${encodeURIComponent(studyId)}/image`,
        session.access_token
      );

      if (!response.ok) {
        throw new Error('Preview unavailable');
      }

      const blob = await response.blob();
      const nextUrl = URL.createObjectURL(blob);

      setScanPreviewUrl(previous => {
        clearObjectUrl(previous);
        return nextUrl;
      });
    } catch (error) {
      setScanPreviewUrl(null);
      setScanPreviewError(
        error instanceof Error ? error.message : 'Preview unavailable'
      );
    }
  };

  const saveStudy = async () => {
    if (!file || !session) return;

    const filename = file.name.toLowerCase();
    const supported = ['.png', '.jpg', '.jpeg'];

    if (!supported.some(extension => filename.endsWith(extension))) {
      setUploadError(
        'Current DenseNet121 inference supports PNG, JPG and JPEG only. DICOM and NIfTI inference is not configured.'
      );
      return;
    }

    setUploadBusy(true);
    setUploadError('');
    setInferenceResult(null);
    setGradcamError('');
    setGradcamPreviewUrl(null);

    try {
      // Upload and run the actual backend inference endpoint.
      const result = await uploadAndAnalyze<InferenceResult>(file);

      setInferenceResult(result);

      // Load the original image from the protected study endpoint.
      const imageResponse = await authFetch(
        `/studies/${encodeURIComponent(result.study_id)}/image`,
        session.access_token
      );

      if (!imageResponse.ok) {
        throw new Error(
          'Inference completed, but the original image preview could not be loaded.'
        );
      }

      const imageBlob = await imageResponse.blob();
      const originalUrl = URL.createObjectURL(imageBlob);

      setScanPreviewUrl(previous => {
        clearObjectUrl(previous);
        return originalUrl;
      });

      // Load the protected Grad-CAM image.
      if (result.gradcam_url) {
        try {
          const apiRoot = API_BASE.replace(/\/api\/v1\/?$/, '');
          const gradcamResponse = await fetch(
            `${apiRoot}${result.gradcam_url}`,
            {
              headers: {
                Authorization: `Bearer ${session.access_token}`
              }
            }
          );

          if (!gradcamResponse.ok) {
            throw new Error('Grad-CAM image could not be loaded.');
          }

          const gradcamBlob = await gradcamResponse.blob();
          const gradcamUrl = URL.createObjectURL(gradcamBlob);

          setGradcamPreviewUrl(previous => {
            clearObjectUrl(previous);
            return gradcamUrl;
          });
        } catch (error) {
          setGradcamError(
            error instanceof Error ? error.message : 'Grad-CAM unavailable'
          );
        }
      }

      setSavedStudy({
        study_id: result.study_id,
        original_filename: file.name,
        content_type: file.type,
        size_bytes: file.size,
        modality: 'XRAY',
        status: result.status,
        created_at: new Date().toISOString()
      });

      await loadStudies();
    } catch (error) {
      setUploadError(
        error instanceof Error
          ? error.message
          : 'Unable to analyze the uploaded image'
      );
    } finally {
      setUploadBusy(false);
    }
  };

  const openStudy = async (studyId: string) => {
    if (!session) return;

    try {
      const response = await authFetch(
        `/studies/${encodeURIComponent(studyId)}`,
        session.access_token
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to load study details');
      }

      setSelectedStudy(data);
      await loadStudyPreview(studyId);
    } catch (error) {
      setStudyError(
        error instanceof Error ? error.message : 'Unable to load study details'
      );
    }
  };

  const exportReport = async (studyId: string) => {
    if (!session) return;

    try {
      const response = await authFetch(
        `/studies/${encodeURIComponent(studyId)}/report`,
        session.access_token
      );

      if (!response.ok) {
        throw new Error('Unable to export report');
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');

      link.href = url;
      link.download = `study-${studyId}.json`;
      link.click();

      URL.revokeObjectURL(url);
    } catch (error) {
      setStudyError(
        error instanceof Error ? error.message : 'Unable to export report'
      );
    }
  };

  const searchLiterature = async () => {
    if (!session) return;

    setLiteratureBusy(true);
    setLiteratureError('');

    try {
      const params = new URLSearchParams({
        q: literatureQuery,
        limit: '10'
      });

      const response = await authFetch(
        `/studies/literature?${params}`,
        session.access_token
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to search PubMed');
      }

      setLiteratureResults(data.articles);
    } catch (error) {
      setLiteratureError(
        error instanceof Error ? error.message : 'Unable to search PubMed'
      );
    } finally {
      setLiteratureBusy(false);
    }
  };

  const loadAdminUsers = async () => {
    if (!session || session.user.role !== 'admin') return;

    try {
      const response = await authFetch('/admin/users', session.access_token);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to load users');
      }

      setAdminUsers(data);
      setAdminUsersError('');
    } catch (error) {
      setAdminUsersError(
        error instanceof Error ? error.message : 'Unable to load users'
      );
    }
  };

  const setUserActive = async (id: number, active: boolean) => {
    if (!session) return;

    try {
      const response = await authFetch(
        `/admin/users/${id}/status`,
        session.access_token,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ active })
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to update account');
      }

      setAdminUsers(rows =>
        rows.map(row => row.id === id ? { ...row, active } : row)
      );
    } catch (error) {
      setAdminUsersError(
        error instanceof Error ? error.message : 'Unable to update account'
      );
    }
  };

  useEffect(() => {
    if (page === 'History') void loadStudies();
  }, [page, query, filter, session]);

  useEffect(() => {
    if (!session || session.user.role !== 'admin' || page !== 'Admin') return;

    let cancelled = false;

    authFetch('/monitoring/summary', session.access_token)
      .then(async response => {
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || 'Unable to load system summary');
        }
        return data;
      })
      .then(data => {
        if (!cancelled) {
          setAdminSummary(data);
          setAdminSummaryError('');
        }
      })
      .catch(error => {
        if (!cancelled) {
          setAdminSummaryError(
            error instanceof Error ? error.message : 'Unable to load summary'
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, [session, page]);

  useEffect(() => {
    return () => {
      clearObjectUrl(scanPreviewUrl);
      clearObjectUrl(gradcamPreviewUrl);
    };
  }, [scanPreviewUrl, gradcamPreviewUrl]);

  if (!session) {
    return (
      <div className="auth-screen">
        <section className="auth-card">
          <div className="auth-brand">
            <span className="brandmark"><HeartPulse size={24}/></span>
            <div>
              <b>MedAI Dx</b>
              <small>AIML-02 · Secure workspace</small>
            </div>
          </div>

          <div className="auth-intro">
            <div className="eyebrow">SECURE ACCESS PORTAL</div>
            <h1>
              {authMode === 'register'
                ? 'Create your account'
                : authPortal === 'admin'
                  ? 'Administrator sign in'
                  : 'Welcome back'}
            </h1>
            <p>
              {authPortal === 'admin'
                ? 'Restricted access for authorized system administrators.'
                : 'Sign in to access your personal medical imaging workspace.'}
            </p>
          </div>

          <div className="auth-switch">
            <button
              className={authPortal === 'user' ? 'selected' : ''}
              onClick={() => {
                setAuthPortal('user');
                setAuthMode('login');
                setAuthError('');
              }}
            >
              <UserCircle size={16}/> User
            </button>
            <button
              className={authPortal === 'admin' ? 'selected' : ''}
              onClick={() => {
                setAuthPortal('admin');
                setAuthMode('login');
                setAuthError('');
              }}
            >
              <Shield size={16}/> Admin
            </button>
          </div>

          <form onSubmit={submitAuth} className="auth-form">
            {authMode === 'register' && (
              <label>
                Full name
                <input
                  value={authName}
                  onChange={event => setAuthName(event.target.value)}
                  required
                  minLength={2}
                  placeholder="Your full name"
                />
              </label>
            )}

            <label>
              Email address
              <input
                type="email"
                value={authEmail}
                onChange={event => setAuthEmail(event.target.value)}
                required
                placeholder="name@example.com"
              />
            </label>

            <label>
              Password
              <input
                type="password"
                value={authPassword}
                onChange={event => setAuthPassword(event.target.value)}
                required
                minLength={authMode === 'register' ? 10 : 1}
                placeholder={
                  authMode === 'register'
                    ? 'At least 10 characters'
                    : 'Enter your password'
                }
              />
            </label>

            {authError && <div className="auth-error">{authError}</div>}

            <button className="primary full" disabled={authBusy}>
              {authBusy
                ? 'Please wait…'
                : authMode === 'register'
                  ? 'Create user account'
                  : `Sign in as ${authPortal}`}
              <ArrowUpRight size={16}/>
            </button>
          </form>

          {authPortal === 'user' && (
            <button
              className="auth-mode-link"
              onClick={() => {
                setAuthMode(authMode === 'login' ? 'register' : 'login');
                setAuthError('');
              }}
            >
              {authMode === 'login'
                ? <><UserPlus size={15}/> Create a new user account</>
                : 'Already registered? Sign in'}
            </button>
          )}

          <div className="auth-security">
            <ShieldCheck size={15}/>
            Role-based access · Secure session · Research use only
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand" onClick={() => choose('Home')}>
          <span className="brandmark"><HeartPulse size={23}/></span>
          <span>
            <b>MedAI Dx</b>
            <small>AIML-02 · Medical imaging workspace</small>
          </span>
        </div>

        <button
          className="mobile-toggle"
          onClick={() => setMobile(!mobile)}
          aria-label="Toggle navigation"
        >
          {mobile ? <X/> : <Menu/>}
        </button>

        <nav className={mobile ? 'nav open' : 'nav'}>
          {nav.map(item => (
            <button
              key={item.name}
              className={page === item.name ? 'active' : ''}
              onClick={() => choose(item.name)}
            >
              <item.icon size={16}/>
              {item.name}
            </button>
          ))}

          {session.user.role === 'admin' && (
            <button
              className={page === 'Admin' ? 'active' : ''}
              onClick={() => choose('Admin')}
            >
              <Settings size={16}/> Admin
            </button>
          )}
        </nav>

        <div className="top-actions">
          <span className="env-pill"><span/> API MODE</span>
          <span className="icon-btn" title="Notifications are not configured">
            <Bell size={18}/>
          </span>
          <span className="role-chip">{session.user.role.toUpperCase()}</span>
          <span className="signed-user">{session.user.full_name}</span>
          <button className="avatar" title="Sign out" onClick={logout}>
            <LogOut size={18}/>
          </button>
        </div>
      </header>

      <main>
        {page === 'Home' && (
          <>
            <section className="hero">
              <div className="hero-copy">
                <div className="eyebrow">
                  <span className="pulse"/> AI-POWERED MEDICAL IMAGING
                </div>
                <h1>
                  AI-Assisted Medical Imaging
                  <br/>
                  <em>and Diagnosis System</em>
                </h1>
                <p>
                  Upload supported X-ray images, explore AI-assisted
                  classification and visual explainability, and review
                  related medical research in one workspace.
                </p>
                <div className="hero-buttons">
                  <button className="primary" onClick={() => choose('Diagnose')}>
                    Analyze a scan <ArrowUpRight size={17}/>
                  </button>
                  <button className="secondary" onClick={() => choose('About')}>
                    About the project
                  </button>
                </div>
                <div className="hero-tags">
                  <span><Brain size={14}/> Classification</span>
                  <span><Microscope size={14}/> Explainable AI</span>
                  <span><BookOpen size={14}/> Study retrieval</span>
                </div>
              </div>

              <div className="hero-art">
                <div className="xray-glow"/>
                <div className="xray-panel">
                  <div className="ribs ribs-left"/>
                  <div className="ribs ribs-right"/>
                  <div className="spine"/>
                  <div className="lung-hotspot"/>
                </div>
                <div className="scan-label">CHEST IMAGING · VISUAL CONCEPT</div>
              </div>

              <div className="hero-side">
                <div className="side-badge">INDUSTRY-LEVEL PORTFOLIO</div>
                <h3>Explainable AI for medical imaging research</h3>
                {[
                  'DenseNet121 classification',
                  'Grad-CAM explainability',
                  'NIH ChestX-ray14 dataset',
                  'FastAPI inference service',
                  'Docker deployment',
                  'MLflow experiment tracking'
                ].map(item => (
                  <div className="checkline" key={item}>
                    <CheckCircle2 size={16}/>{item}
                  </div>
                ))}
              </div>
            </section>

            <section className="stats">
              <Stat icon={<ScanLine/>} value="1" label="Inference modality"/>
              <Stat icon={<FileImage/>} value="3" label="Inference image formats"/>
              <Stat icon={<Layers3/>} value="6" label="Core workspace modules"/>
              <Stat icon={<BookOpen/>} value="Research" label="Intended use"/>
            </section>

            <SectionTitle
              kicker="PLATFORM WORKSPACE"
              title="Explore the six core modules"
              action="Open diagnosis"
              onAction={() => choose('Diagnose')}
            />

            <div className="module-grid">
              {[
                {
                  icon: <UploadCloud/>,
                  title: 'Upload & Analyze',
                  desc: 'Upload PNG, JPG or JPEG X-ray images for DenseNet121 inference.',
                  p: 'Diagnose' as Page
                },
                {
                  icon: <Brain/>,
                  title: 'Diagnosis Results',
                  desc: 'Classification output and Grad-CAM explanation.',
                  p: 'Diagnose' as Page
                },
                {
                  icon: <BookOpen/>,
                  title: 'Similar Studies & References',
                  desc: 'Similar-case retrieval and medical literature workspace.',
                  p: 'Studies' as Page
                },
                {
                  icon: <History/>,
                  title: 'History / Patient Records',
                  desc: 'Search and review study records and dates.',
                  p: 'History' as Page
                },
                {
                  icon: <ChartNoAxesCombined/>,
                  title: 'Admin / Model Monitoring',
                  desc: 'Model status, experiments, drift and service health.',
                  p: 'Admin' as Page
                },
                {
                  icon: <Info/>,
                  title: 'About AIML-02',
                  desc: 'Project overview, architecture and responsible-use notes.',
                  p: 'About' as Page
                }
              ].filter(item =>
                item.p !== 'Admin' || session.user.role === 'admin'
              ).map(item => (
                <button
                  className="module-card"
                  onClick={() => choose(item.p)}
                  key={item.title}
                >
                  <span className="module-icon">{item.icon}</span>
                  <h3>{item.title}</h3>
                  <p>{item.desc}</p>
                  <span className="module-link">
                    Open module <ChevronRight size={15}/>
                  </span>
                </button>
              ))}
            </div>

            <SectionTitle
              kicker="SYSTEM DESIGN"
              title="Overall architecture"
              action="Read about the project"
              onAction={() => choose('About')}
            />

            <section className="architecture panel">
              <div className="architecture-flow">
                <ArchNode icon={<UserCircle/>} title="User" sub="Web application"/>
                <Arrow/>
                <ArchNode icon={<Layers3/>} title="React" sub="Frontend viewer"/>
                <Arrow/>
                <ArchNode icon={<Server/>} title="FastAPI" sub="Backend API"/>
                <Arrow/>
                <ArchNode icon={<Brain/>} title="DenseNet121" sub="X-ray classifier"/>
              </div>
              <div className="architecture-connect">
                <span>Backend service integrations</span>
              </div>
              <div className="service-grid">
                {[
                  ['Orthanc', 'DICOM server'],
                  ['MLflow', 'Experiment tracking'],
                  ['Feast', 'Feature store'],
                  ['Evidently AI', 'Data drift monitoring']
                ].map(item => (
                  <div className="service-node" key={item[0]}>
                    <Database size={18}/>
                    <b>{item[0]}</b>
                    <small>{item[1]}</small>
                  </div>
                ))}
              </div>
            </section>

            <SectionTitle
              kicker="TECHNOLOGY"
              title="Technology stack"
              action="View details"
              onAction={() => choose('About')}
            />

            <div className="stack-grid">
              {[
                { icon: <Layers3/>, title: 'Frontend', items: 'React · TypeScript' },
                { icon: <Server/>, title: 'Backend', items: 'FastAPI · Python · Pydantic' },
                { icon: <Brain/>, title: 'AI / ML', items: 'PyTorch · DenseNet121 · Grad-CAM' },
                { icon: <Database/>, title: 'Data', items: 'NIH ChestX-ray14' },
                { icon: <ChartNoAxesCombined/>, title: 'Monitoring', items: 'MLflow · Evidently AI' },
                { icon: <GitBranch/>, title: 'Deployment', items: 'Docker · GitHub Actions' }
              ].map(item => (
                <div className="stack-card" key={item.title}>
                  <span>{item.icon}</span>
                  <div><b>{item.title}</b><p>{item.items}</p></div>
                </div>
              ))}
            </div>

            <SectionTitle
              kicker="SUBMISSION"
              title="Key deliverables & evaluation"
              action="See project checklist"
              onAction={() => choose('About')}
            />

            <section className="panel deliverables">
              <div className="deliverable-grid">
                {deliverables.map(item => (
                  <div key={item}><CheckCircle2 size={17}/>{item}</div>
                ))}
              </div>
            </section>
          </>
        )}

        {page === 'Diagnose' && (
          <>
            <PageHeading
              kicker="IMAGING WORKSPACE"
              title="Upload medical scan"
              desc="Upload a supported chest X-ray image and run the configured DenseNet121 research model."
            />

            <div className="diagnose-layout">
              <section className="panel upload-panel">
                <div className="panel-head">
                  <div>
                    <h3><UploadCloud size={18}/> Upload scan</h3>
                    <p>Choose a supported X-ray image</p>
                  </div>
                  <span className="step-chip">STEP 01</span>
                </div>

                <label
                  className="dropzone"
                  onDragOver={event => event.preventDefault()}
                  onDrop={event => {
                    event.preventDefault();
                    upload(event.dataTransfer.files[0]);
                  }}
                >
                  <input
                    type="file"
                    accept=".png,.jpg,.jpeg"
                    onChange={event => upload(event.target.files?.[0])}
                  />
                  <span className="upload-icon"><UploadCloud size={28}/></span>
                  <b>Drag & drop your X-ray here</b>
                  <span>or <u>browse files</u></span>
                  <small>Supported for inference: PNG · JPG · JPEG</small>
                  <small>Maximum upload: 100 MB</small>
                </label>

                {file && (
                  <div className="file-row">
                    <FileImage size={19}/>
                    <div>
                      <b>{file.name}</b>
                      <small>
                        {(file.size / 1024).toFixed(1)} KB · Ready for analysis
                      </small>
                    </div>
                    <button
                      onClick={() => {
                        setFile(null);
                        setSavedStudy(null);
                        setInferenceResult(null);
                        clearObjectUrl(scanPreviewUrl);
                        clearObjectUrl(gradcamPreviewUrl);
                        setScanPreviewUrl(null);
                        setGradcamPreviewUrl(null);
                      }}
                    >
                      <X size={16}/>
                    </button>
                  </div>
                )}

                {uploadError && <div className="auth-error">{uploadError}</div>}

                <div className="privacy-note">
                  <ShieldCheck size={16}/>
                  Uploads are stored in your private account. Do not upload
                  identifiable patient information.
                </div>

                <button
                  className="primary full"
                  disabled={!file || uploadBusy}
                  onClick={saveStudy}
                >
                  {uploadBusy ? 'Analyzing image…' : 'Run AI analysis'}
                  <ArrowUpRight size={17}/>
                </button>

                {inferenceResult && (
                  <div className="notice success">
                    <CheckCircle2 size={17}/>
                    Inference completed. Study ID: {inferenceResult.study_id}
                  </div>
                )}
              </section>

              <section className="panel process-panel">
                <div className="panel-head">
                  <div>
                    <h3>Analysis pipeline</h3>
                    <p>Backend inference workflow</p>
                  </div>
                  <span className="step-chip">WORKFLOW</span>
                </div>

                {[
                  ['01', 'Image upload', 'PNG/JPG/JPEG validation'],
                  ['02', 'Image preprocessing', 'Resize and normalization'],
                  ['03', 'DenseNet121 inference', '14-label classification'],
                  ['04', 'Grad-CAM', 'Visual explanation generation'],
                  ['05', 'Study storage', 'Authenticated study record']
                ].map((step, index) => {
                  const done = Boolean(inferenceResult);
                  return (
                    <div className="process-step" key={step[0]}>
                      <span className={done ? 'step-number done' : 'step-number'}>
                        {step[0]}
                      </span>
                      <div>
                        <b>{step[1]}</b>
                        <small>{step[2]}</small>
                      </div>
                      {done
                        ? <CheckCircle2 size={17}/>
                        : <ChevronRight size={16}/>}
                    </div>
                  );
                })}

                <div className="pipeline-foot">
                  <Cpu size={17}/>
                  Model: NIH14-baseline-v1 · CPU inference
                </div>
              </section>
            </div>

            <section className="panel result-panel">
              <div className="panel-head">
                <div>
                  <h3>Analysis output</h3>
                  <p>
                    Model output is experimental and is not a clinical diagnosis.
                  </p>
                </div>
                <span className="step-chip">
                  {inferenceResult ? 'ANALYSIS COMPLETE' : 'AWAITING ANALYSIS'}
                </span>
              </div>

              <div className="result-grid">
                {scanPreviewUrl ? (
                  <div className="image-placeholder">
                    <img
                      style={{
                        width: '100%',
                        height: '100%',
                        objectFit: 'contain'
                      }}
                      src={scanPreviewUrl}
                      alt="Original X-ray"
                    />
                  </div>
                ) : (
                  <ImagePlaceholder
                    title="Original scan"
                    sub={file?.name || 'No uploaded image'}
                  />
                )}

                {gradcamPreviewUrl ? (
                  <div className="image-placeholder">
                    <img
                      style={{
                        width: '100%',
                        height: '100%',
                        objectFit: 'contain'
                      }}
                      src={gradcamPreviewUrl}
                      alt="Grad-CAM visualization"
                    />
                  </div>
                ) : (
                  <ImagePlaceholder
                    title="Grad-CAM"
                    sub={gradcamError || 'No visualization available'}
                  />
                )}

                <ImagePlaceholder
                  title="Segmentation"
                  sub="Not implemented in current inference flow"
                />

                <div className="prediction-card">
                  <span className="muted">PREDICTED LABEL</span>

                  <h2>
                    {inferenceResult?.predicted_label || 'Not available'}
                  </h2>

                  <p>
                    {inferenceResult?.disclaimer ||
                      'Run an X-ray analysis to view model output.'}
                  </p>

                  <div className="model-meta">
                    <b>Model</b>
                    <span>{inferenceResult?.model_name || 'Unavailable'}</span>
                  </div>

                  <div className="model-meta">
                    <b>Version</b>
                    <span>{inferenceResult?.model_version || 'Unavailable'}</span>
                  </div>

                  <div className="model-meta">
                    <b>Status</b>
                    <span>{inferenceResult?.status || 'Pending'}</span>
                  </div>

                  <div>
                    <b>Top predictions</b>

                    {inferenceResult?.top_predictions?.map(prediction => (
                      <div className="model-meta" key={prediction.label}>
                        <span>{prediction.label}</span>
                        <b>
                          {(prediction.probability * 100).toFixed(2)}%
                        </b>
                      </div>
                    ))}
                  </div>

                  <p>
                    Displayed values are raw model scores, not calibrated
                    probabilities or confirmed diagnoses.
                  </p>

                  {inferenceResult?.probability_note && (
                    <p>{inferenceResult.probability_note}</p>
                  )}

                  <button
                    className="secondary"
                    disabled={!savedStudy}
                    onClick={() =>
                      savedStudy && exportReport(savedStudy.study_id)
                    }
                  >
                    <Download size={14}/> Export study report (JSON)
                  </button>
                </div>
              </div>

              {scanPreviewError && (
                <div className="table-foot">{scanPreviewError}</div>
              )}

              <div className="integration-note">
                <AlertTriangle size={16}/>
                Research use only. Model outputs are not clinically validated
                and must not guide diagnosis or treatment.
              </div>
            </section>
          </>
        )}

        {page === 'Studies' && (
          <>
            <PageHeading
              kicker="KNOWLEDGE EXPLORER"
              title="Similar cases & medical references"
              desc="Explore the available case retrieval and medical literature integrations."
            />

            <div className="tabs">
              {['Similar Cases', 'Research Articles'].map(item => (
                <button
                  className={tab === item ? 'selected' : ''}
                  onClick={() => setTab(item)}
                  key={item}
                >
                  {item}
                </button>
              ))}
            </div>

            {tab === 'Similar Cases' ? (
              <section className="panel">
                <div className="panel-head">
                  <div>
                    <h3>Similar case retrieval</h3>
                    <p>No approved embedding index is configured</p>
                  </div>
                  <span className="step-chip">NOT CONFIGURED</span>
                </div>
                <div className="retrieval-info">
                  <Database/>
                  <b>Case retrieval is unavailable</b>
                  <p>
                    A validated embedding model and approved de-identified
                    case index are required. No example similarity scores
                    are fabricated.
                  </p>
                </div>
              </section>
            ) : (
              <section className="panel literature">
                <div className="panel-head">
                  <div>
                    <h3>Medical research literature</h3>
                    <p>Live search via PubMed E-utilities</p>
                  </div>
                  <ExternalLink size={18}/>
                </div>

                <form
                  className="table-toolbar"
                  onSubmit={event => {
                    event.preventDefault();
                    void searchLiterature();
                  }}
                >
                  <div className="searchbox">
                    <Search size={17}/>
                    <input
                      value={literatureQuery}
                      onChange={event => setLiteratureQuery(event.target.value)}
                      minLength={3}
                      maxLength={200}
                      required
                      placeholder="Search a general medical topic…"
                    />
                  </div>
                  <button className="primary" disabled={literatureBusy}>
                    {literatureBusy ? 'Searching…' : 'Search PubMed'}
                  </button>
                </form>

                <p className="table-foot">
                  Do not enter patient names, identifiers, or protected health
                  information into literature searches.
                </p>

                {literatureError && (
                  <div className="auth-error">{literatureError}</div>
                )}

                {literatureResults.map(article => (
                  <div className="article-row" key={article.pmid}>
                    <span><BookOpen size={16}/></span>
                    <div>
                      <b>{article.title || 'Untitled article'}</b>
                      <small>
                        {[
                          article.journal,
                          article.year,
                          article.pmid && `PMID ${article.pmid}`
                        ].filter(Boolean).join(' · ')}
                      </small>
                    </div>
                    {article.url && (
                      <a
                        href={article.url}
                        target="_blank"
                        rel="noreferrer"
                        aria-label="Open PubMed article"
                      >
                        <ExternalLink size={15}/>
                      </a>
                    )}
                  </div>
                ))}

                {literatureResults.length === 0 &&
                  !literatureBusy &&
                  !literatureError && (
                    <div className="empty-state">
                      Enter a research topic to search PubMed.
                    </div>
                  )}
              </section>
            )}
          </>
        )}

        {page === 'History' && (
          <>
            <PageHeading
              kicker="STUDY MANAGEMENT"
              title="Analysis history"
              desc="Search and review study records belonging to your account."
            />

            <section className="panel">
              <div className="table-toolbar">
                <div className="searchbox">
                  <Search size={17}/>
                  <input
                    placeholder="Search by study ID or filename..."
                    value={query}
                    onChange={event => setQuery(event.target.value)}
                  />
                </div>

                <select
                  value={filter}
                  onChange={event => setFilter(event.target.value)}
                >
                  <option>All studies</option>
                  <option>X-ray</option>
                  <option>CT</option>
                  <option>MRI</option>
                  <option>UNKNOWN</option>
                </select>

                <button
                  className="secondary"
                  onClick={() => void loadStudies()}
                  disabled={studyBusy}
                >
                  <SlidersHorizontal size={16}/>
                  {studyBusy ? 'Loading…' : 'Refresh'}
                </button>
              </div>

              {studyError && <div className="auth-error">{studyError}</div>}

              {selectedStudy && (
                <div className="file-row">
                  <FileText size={19}/>
                  <div>
                    <b>{selectedStudy.original_filename}</b>
                    <small>
                      {selectedStudy.study_id} · {selectedStudy.modality} ·
                      {selectedStudy.status} ·
                      {(selectedStudy.size_bytes / 1024).toFixed(1)} KB
                    </small>
                  </div>
                  <button
                    className="secondary small"
                    onClick={() => void exportReport(selectedStudy.study_id)}
                  >
                    Export report
                  </button>
                  <button
                    onClick={() => setSelectedStudy(null)}
                    aria-label="Close study details"
                  >
                    <X size={16}/>
                  </button>
                </div>
              )}

              {selectedStudy && scanPreviewUrl && (
                <img
                  style={{
                    display: 'block',
                    maxWidth: '100%',
                    maxHeight: 420,
                    objectFit: 'contain',
                    margin: '12px auto'
                  }}
                  src={scanPreviewUrl}
                  alt="Selected medical scan"
                />
              )}

              {selectedStudy && scanPreviewError && (
                <div className="table-foot">{scanPreviewError}</div>
              )}

              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>STUDY ID</th>
                      <th>MODALITY</th>
                      <th>FILE</th>
                      <th>DATE</th>
                      <th>STATUS</th>
                      <th>ACTION</th>
                    </tr>
                  </thead>
                  <tbody>
                    {studies.map(study => (
                      <tr key={study.study_id}>
                        <td><b>{study.study_id.slice(0, 8)}</b></td>
                        <td>{study.modality}</td>
                        <td>{study.original_filename}</td>
                        <td>
                          {study.created_at
                            ? new Date(
                                `${study.created_at}Z`
                              ).toLocaleString()
                            : '—'}
                        </td>
                        <td>
                          <span className="status">
                            <span/>{study.status}
                          </span>
                        </td>
                        <td>
                          <button
                            className="icon-btn"
                            title="View study details"
                            onClick={() => void openStudy(study.study_id)}
                          >
                            <Eye size={16}/>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {studies.length === 0 && (
                  <div className="empty-state">
                    {studyBusy
                      ? 'Loading your studies…'
                      : 'No matching studies in your account.'}
                  </div>
                )}
              </div>

              <p className="table-foot">
                Study records are private to your authenticated account.
              </p>
            </section>
          </>
        )}

        {page === 'Admin' && session.user.role === 'admin' && (
          <section className="admin-shell">
            <aside className="admin-sidebar">
              <div className="admin-side-heading">
                <span className="admin-side-mark"><Activity size={18}/></span>
                <div>
                  <b>Admin Console</b>
                  <small>MODEL OPERATIONS</small>
                </div>
              </div>

              <div className="admin-side-label">WORKSPACE</div>

              {[
                ['Dashboard', LayoutDashboard],
                ['User Management', UserCircle],
                ['Model Experiments', FlaskConical],
                ['Data & Datasets', Database],
                ['Model Monitoring', Activity],
                ['System Health', Hospital]
              ].map(([label, Icon]: any) => (
                <button
                  key={label}
                  className={
                    adminTab === label
                      ? 'admin-side-link selected'
                      : 'admin-side-link'
                  }
                  onClick={() => {
                    setAdminTab(label);
                    if (label === 'User Management') void loadAdminUsers();
                  }}
                >
                  <Icon size={16}/><span>{label}</span>
                </button>
              ))}

              <div className="admin-side-bottom">
                <ShieldCheck size={16}/>
                <span>Governance & audit</span>
                <small>Research workspace</small>
              </div>
            </aside>

            <div className="admin-content">
              <div className="admin-page-top">
                <div>
                  <div className="admin-kicker">AIML-02 / ADMINISTRATION</div>
                  <h1>{adminTab === 'Dashboard' ? 'System overview' : adminTab}</h1>
                  <p>Operational workspace for {adminTab.toLowerCase()}.</p>
                </div>
                <div className="admin-date">
                  <span className="live-dot"/> LIVE API
                  <small>Research environment</small>
                </div>
              </div>

              {adminSummaryError && (
                <div className="auth-error">{adminSummaryError}</div>
              )}

              {adminTab === 'Dashboard' && (
                <>
                  {adminSummary ? (
                    <div className="admin-metrics">
                      <div className="admin-metric metric-green">
                        <div>
                          <span>Registered users</span>
                          <small>BACKEND ACCOUNT TOTAL</small>
                        </div>
                        <b>{adminSummary.metrics.registered_users}</b>
                        <em>Actual database count</em>
                      </div>

                      <div className="admin-metric metric-blue">
                        <div>
                          <span>Stored studies</span>
                          <small>BACKEND STUDY TOTAL</small>
                        </div>
                        <b>{adminSummary.metrics.stored_studies}</b>
                        <em>Actual database count</em>
                      </div>

                      <div className="admin-metric metric-purple">
                        <div>
                          <span>Model inference</span>
                          <small>CLASSIFICATION / SEGMENTATION</small>
                        </div>
                        <b>{adminSummary.model.status}</b>
                        <em>{adminSummary.model.reason}</em>
                      </div>
                    </div>
                  ) : (
                    <div className="monitoring-placeholder">
                      Loading live backend summary…
                    </div>
                  )}

                  <div className="admin-lower-grid">
                    <section className="admin-card">
                      <div className="admin-card-head">
                        <div>
                          <h3>Platform services</h3>
                          <p>Live configured-service reachability</p>
                        </div>
                        <Server size={17}/>
                      </div>

                      {adminSummary &&
                        Object.entries(adminSummary.services).map(
                          ([name, service]) => (
                            <div className="service-status" key={name}>
                              <span className="service-dot"/>
                              <div>
                                <b>{name.toUpperCase()}</b>
                                <small>Backend integration</small>
                              </div>
                              <em>
                                {service.status}
                                {service.http_status
                                  ? ` (${service.http_status})`
                                  : ''}
                              </em>
                            </div>
                          )
                        )}
                    </section>

                    <section className="admin-card">
                      <div className="admin-card-head">
                        <div>
                          <h3>Monitoring & experiments</h3>
                          <p>No synthetic metrics are displayed</p>
                        </div>
                        <ShieldCheck size={17}/>
                      </div>
                      <div className="monitoring-placeholder">
                        <ChartNoAxesCombined size={32}/>
                        <b>Model quality and drift status</b>
                        <p>
                          {adminSummary?.drift.reason ||
                            'Monitoring status is unavailable.'}
                        </p>
                      </div>
                    </section>
                  </div>
                </>
              )}

              {adminTab === 'User Management' && (
                <section className="admin-card admin-subpage">
                  <div className="admin-card-head">
                    <div>
                      <h3>Registered users</h3>
                      <p>
                        Manage account access. Admin role assignment is
                        intentionally not available here.
                      </p>
                    </div>
                    <UserCircle size={18}/>
                  </div>

                  {adminUsersError && (
                    <div className="auth-error">{adminUsersError}</div>
                  )}

                  <div className="admin-table">
                    <div className="admin-table-head user-table-head">
                      <span>NAME</span>
                      <span>EMAIL</span>
                      <span>ROLE</span>
                      <span>STATUS</span>
                      <span>ACTION</span>
                    </div>

                    {adminUsers.map(user => (
                      <div
                        className="admin-table-row user-table-row"
                        key={user.id}
                      >
                        <span>{user.full_name}</span>
                        <span>{user.email}</span>
                        <span>{user.role}</span>
                        <span>{user.active ? 'Active' : 'Disabled'}</span>
                        <span>
                          {user.role === 'user' ? (
                            <button
                              className="admin-view-all"
                              onClick={() =>
                                void setUserActive(user.id, !user.active)
                              }
                            >
                              {user.active ? 'Disable' : 'Enable'}
                            </button>
                          ) : 'Protected admin'}
                        </span>
                      </div>
                    ))}
                  </div>

                  {adminUsers.length === 0 && !adminUsersError && (
                    <div className="empty-state">
                      No accounts found or user list has not loaded.
                    </div>
                  )}
                </section>
              )}

              {adminTab === 'Model Experiments' && (
                <AdminPlaceholder
                  icon={<FlaskConical size={32}/>}
                  title="No experiment registry is connected"
                  description="Configure MLFLOW_TRACKING_URI and register real training runs before experiment results can be displayed."
                />
              )}

              {adminTab === 'Data & Datasets' && (
                <AdminPlaceholder
                  icon={<Database size={32}/>}
                  title="Dataset registry is not configured"
                  description="Register downloaded, versioned and approved datasets before displaying dataset records."
                />
              )}

              {adminTab === 'Model Monitoring' && (
                <AdminPlaceholder
                  icon={<ChartNoAxesCombined size={32}/>}
                  title="Monitoring reports"
                  description={
                    adminSummary?.drift.reason ||
                    'Configure Evidently AI with reference and current datasets to generate measured monitoring reports.'
                  }
                />
              )}

              {adminTab === 'System Health' && (
                <section className="admin-card admin-subpage">
                  <div className="admin-card-head">
                    <div>
                      <h3>System health</h3>
                      <p>Live service availability from the backend</p>
                    </div>
                    <Hospital size={18}/>
                  </div>

                  {adminSummary
                    ? Object.entries(adminSummary.services).map(
                        ([name, service]) => (
                          <div className="service-status" key={name}>
                            <span className="service-dot"/>
                            <div>
                              <b>{name.toUpperCase()}</b>
                              <small>Backend integration</small>
                            </div>
                            <em>
                              {service.status}
                              {service.http_status
                                ? ` (${service.http_status})`
                                : ''}
                            </em>
                          </div>
                        )
                      )
                    : <div className="monitoring-placeholder">Loading service status…</div>}
                </section>
              )}
            </div>
          </section>
        )}

        {page === 'About' && (
          <>
            <PageHeading
              kicker="ABOUT AIML-02"
              title="AI-Assisted Medical Imaging and Diagnosis System"
              desc="A research-oriented platform combining medical image workflows, deep learning, explainability and medical literature review."
            />

            <section className="about-hero panel">
              <div className="about-icon"><Stethoscope size={30}/></div>
              <div>
                <h2>Make medical imaging AI more transparent.</h2>
                <p>
                  This project demonstrates an X-ray classification workflow
                  with Grad-CAM visualization, authenticated study storage
                  and medical literature review.
                </p>
              </div>
            </section>

            <div className="about-grid">
              <section className="panel">
                <h3><Gauge size={18}/> Project objectives</h3>
                <ul>
                  <li>Provide a structured upload and imaging review workflow.</li>
                  <li>Expose classification output with model/version metadata.</li>
                  <li>Visualize Grad-CAM explanations.</li>
                  <li>Connect DICOM studies through a server-side adapter.</li>
                  <li>Support research retrieval and experiment monitoring.</li>
                </ul>
              </section>

              <section className="panel">
                <h3><Workflow size={18}/> End-to-end workflow</h3>
                <ol>
                  <li>Choose a permitted public dataset.</li>
                  <li>Preprocess and version data.</li>
                  <li>Train and evaluate a classification model.</li>
                  <li>Generate Grad-CAM overlays.</li>
                  <li>Expose inference via FastAPI.</li>
                  <li>Track tests and deployment.</li>
                </ol>
              </section>

              <section className="panel">
                <h3><Database size={18}/> Dataset & resources</h3>
                <ul>
                  <li>NIH ChestX-ray14</li>
                  <li>CheXpert</li>
                  <li>MIMIC-CXR (credentialed access)</li>
                  <li>RSNA Pneumonia Detection</li>
                  <li>Medical Segmentation Decathlon</li>
                </ul>
                <p className="small-note">
                  Dataset access and use depend on licence and permissions.
                </p>
              </section>

              <section className="panel">
                <h3><LockKeyhole size={18}/> Responsible use & limitations</h3>
                <ul>
                  <li>Educational / research prototype only.</li>
                  <li>No diagnosis or treatment decision should rely on demo output.</li>
                  <li>Do not upload identifiable patient data.</li>
                  <li>Report dataset limitations, bias and external validation.</li>
                  <li>Clinical use requires regulatory and security review.</li>
                </ul>
              </section>
            </div>

            <section className="panel about-stack">
              <div className="panel-head">
                <div>
                  <h3>Technology and integrations</h3>
                  <p>Project components</p>
                </div>
                <Sparkles size={18}/>
              </div>

              <div className="stack-grid compact">
                {[
                  ['Frontend', 'React · TypeScript'],
                  ['Backend', 'FastAPI · Python'],
                  ['Classification', 'PyTorch · DenseNet121'],
                  ['Segmentation', 'MONAI · Not integrated'],
                  ['Imaging', 'X-ray · DICOM integration'],
                  ['Explainability', 'Grad-CAM'],
                  ['Data versioning', 'DVC'],
                  ['Monitoring', 'MLflow · Evidently AI'],
                  ['Deployment', 'Docker · CI/CD']
                ].map(item => (
                  <div className="stack-card" key={item[0]}>
                    <span><Cpu/></span>
                    <div><b>{item[0]}</b><p>{item[1]}</p></div>
                  </div>
                ))}
              </div>
            </section>
          </>
        )}
      </main>

      <footer>
        <div className="footer-brand">
          <HeartPulse size={18}/> MedAI Dx <span>AIML-02</span>
        </div>
        <p>
          Educational / research prototype · Not for clinical use
        </p>
        <button onClick={() => choose('About')}>
          About <ChevronRight size={13}/>
        </button>
        <span>© 2026 MedAI Dx</span>
      </footer>
    </div>
  );
}

function AdminPlaceholder({
  icon,
  title,
  description
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <section className="admin-card admin-subpage">
      <div className="monitoring-placeholder">
        {icon}
        <b>{title}</b>
        <p>{description}</p>
      </div>
    </section>
  );
}

function Stat({ icon, value, label }: any) {
  return (
    <div className="stat">
      <span>{icon}</span>
      <b>{value}</b>
      <small>{label}</small>
    </div>
  );
}

function SectionTitle({
  kicker,
  title,
  action,
  onAction
}: any) {
  return (
    <div className="section-title">
      <div>
        <small>{kicker}</small>
        <h2>{title}</h2>
      </div>
      <button className="text-action" onClick={onAction}>
        {action} <ArrowUpRight size={16}/>
      </button>
    </div>
  );
}

function PageHeading({ kicker, title, desc }: any) {
  return (
    <div className="page-heading">
      <div className="eyebrow">{kicker}</div>
      <h1>{title}</h1>
      <p>{desc}</p>
    </div>
  );
}

function ArchNode({ icon, title, sub }: any) {
  return (
    <div className="arch-node">
      <span>{icon}</span>
      <b>{title}</b>
      <small>{sub}</small>
    </div>
  );
}

function Arrow() {
  return <ChevronRight className="arch-arrow"/>;
}

function ImagePlaceholder({ title, sub }: any) {
  return (
    <div className="image-placeholder">
      <ScanLine size={30}/>
      <b>{title}</b>
      <small>{sub}</small>
    </div>
  );
}

export default App;
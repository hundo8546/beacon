import { initializeApp } from "firebase/app";
import { getAnalytics, isSupported } from "firebase/analytics";
import {
  RecaptchaVerifier,
  createUserWithEmailAndPassword,
  getAuth,
  onAuthStateChanged,
  signInAnonymously,
  signInWithEmailAndPassword,
  signInWithPhoneNumber,
  signOut,
  updateProfile,
} from "firebase/auth";
import {
  addDoc,
  collection,
  deleteDoc,
  doc,
  getDocs,
  getFirestore,
  limit,
  onSnapshot,
  orderBy,
  query,
  serverTimestamp,
  setDoc,
} from "firebase/firestore";
import { getFunctions, httpsCallable } from "firebase/functions";
import { demoAnalysisRun, demoBuyIdeas, demoFactorIc, demoHoldings, demoSignals } from "./demoData";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "",
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "",
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "",
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || "",
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || "",
  appId: import.meta.env.VITE_FIREBASE_APP_ID || "",
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID || "",
};

export const firebaseReady = Boolean(firebaseConfig.apiKey && firebaseConfig.projectId && firebaseConfig.appId);
export const app = firebaseReady ? initializeApp(firebaseConfig) : null;
export const auth = app ? getAuth(app) : null;
export const db = app ? getFirestore(app) : null;
export const functions = app ? getFunctions(app) : null;

if (firebaseReady && typeof window !== "undefined") {
  isSupported().then((supported) => {
    if (supported) getAnalytics(app);
  });
}

export async function ensureUserProfile() {
  requireFirebase();
  const user = await new Promise((resolve, reject) => {
    const unsubscribe = onAuthStateChanged(
      auth,
      async (current) => {
        unsubscribe();
        if (current) {
          resolve(current);
          return;
        }
        resolve(null);
      },
      reject,
    );
  });

  if (!user) return { user: null };
  await ensureProfileForUser(user);
  return { user };
}

export async function ensureProfileForUser(user) {
  requireFirebase();
  await setDoc(
    doc(db, "users", user.uid),
    {
      email: user.email || null,
      displayName: user.displayName || user.phoneNumber || "Beacon Investor",
      phoneNumber: user.phoneNumber || null,
      isAnonymous: user.isAnonymous,
      createdAt: serverTimestamp(),
      lastLoginAt: serverTimestamp(),
      defaultRiskStyle: "Balanced",
      defaultTaxRate: 0.24,
      openAiEnabled: false,
      subscriptionTier: "local-dev",
    },
    { merge: true },
  );
  return { user };
}

export async function signInWithAnonymousTestUser() {
  requireFirebase();
  const credential = await signInAnonymously(auth);
  await ensureProfileForUser(credential.user);
  return credential.user;
}

export async function signInWithEmail(email, password) {
  requireFirebase();
  const credential = await signInWithEmailAndPassword(auth, email, password);
  await ensureProfileForUser(credential.user);
  return credential.user;
}

export async function createEmailAccount(email, password, displayName) {
  requireFirebase();
  const credential = await createUserWithEmailAndPassword(auth, email, password);
  if (displayName) {
    await updateProfile(credential.user, { displayName });
  }
  await ensureProfileForUser(credential.user);
  return credential.user;
}

export async function signOutOfFirebase() {
  requireFirebase();
  await signOut(auth);
}

export function createPhoneRecaptcha(containerId = "recaptcha-container") {
  requireFirebase();
  if (window.beaconRecaptchaVerifier) {
    window.beaconRecaptchaVerifier.clear();
    window.beaconRecaptchaVerifier = null;
  }
  window.beaconRecaptchaVerifier = new RecaptchaVerifier(auth, containerId, {
    size: "normal",
    callback: () => {},
    "expired-callback": () => {},
  });
  return window.beaconRecaptchaVerifier;
}

export async function sendPhoneVerificationCode(phoneNumber, containerId = "recaptcha-container") {
  const verifier = createPhoneRecaptcha(containerId);
  await verifier.render();
  const confirmation = await signInWithPhoneNumber(auth, phoneNumber, verifier);
  window.beaconPhoneConfirmation = confirmation;
  return confirmation;
}

export async function confirmPhoneVerificationCode(code) {
  const confirmation = window.beaconPhoneConfirmation;
  if (!confirmation) {
    throw new Error("Send a phone verification code first.");
  }
  const credential = await confirmation.confirm(code);
  await ensureProfileForUser(credential.user);
  return credential.user;
}

export function subscribeToBeaconData(userId, setState) {
  requireFirebase();
  const updates = {
    user: auth.currentUser,
    profile: null,
    brokerConnections: [],
    holdings: [],
    latestRun: null,
    actions: [],
    buyIdeas: [],
    factorIc: [],
    signals: [],
    plan: null,
    loading: false,
    error: null,
  };
  const apply = (patch) => {
    Object.assign(updates, patch);
    setState((current) => ({ ...current, ...updates }));
  };
  const onError = (error) => apply({ loading: false, error: firestoreErrorMessage(error) });

  const subscriptions = [
    onSnapshot(
      doc(db, "users", userId),
      (snapshot) => apply({ profile: { id: snapshot.id, ...snapshot.data() } }),
      onError,
    ),
    onSnapshot(
      collection(db, "users", userId, "brokerConnections"),
      (snapshot) => apply({ brokerConnections: snapshot.docs.map(normalizeDoc) }),
      onError,
    ),
    onSnapshot(
      collection(db, "users", userId, "holdings"),
      (snapshot) => apply({ holdings: snapshot.docs.map((item) => normalizeHolding(normalizeDoc(item))) }),
      onError,
    ),
    onSnapshot(
      query(collection(db, "users", userId, "analysisRuns"), orderBy("createdAt", "desc"), limit(1)),
      async (snapshot) => {
        const latestRun = snapshot.docs[0] ? normalizeDoc(snapshot.docs[0]) : null;
        if (!latestRun) {
          apply({ latestRun: null, actions: [], buyIdeas: [], plan: null });
          return;
        }
        const [actionsSnap, ideasSnap, planSnap] = await Promise.all([
          getDocs(collection(db, "users", userId, "analysisRuns", latestRun.id, "actions")),
          getDocs(collection(db, "users", userId, "analysisRuns", latestRun.id, "buyIdeas")),
          getDocs(collection(db, "users", userId, "analysisRuns", latestRun.id, "investmentPlan")),
        ]);
        apply({
          latestRun: normalizeAnalysis(latestRun),
          actions: actionsSnap.docs.map((item) => normalizeSignal(normalizeDoc(item))),
          buyIdeas: ideasSnap.docs.map((item) => normalizeIdea(normalizeDoc(item))),
          plan: planSnap.docs[0] ? normalizeDoc(planSnap.docs[0]) : null,
        });
      },
      onError,
    ),
    onSnapshot(
      collection(db, "users", userId, "factorIcLog"),
      (snapshot) => apply({ factorIc: snapshot.docs.map((item) => normalizeFactor(normalizeDoc(item))) }),
      onError,
    ),
    onSnapshot(
      collection(db, "users", userId, "strategySignals"),
      (snapshot) => apply({ signals: snapshot.docs.map((item) => normalizeSignal(normalizeDoc(item))) }),
      onError,
    ),
  ];
  return () => subscriptions.forEach((unsubscribe) => unsubscribe());
}

export async function seedDemoData(userId) {
  requireFirebase();
  const runRef = await addDoc(collection(db, "users", userId, "analysisRuns"), {
    ...demoAnalysisRun,
    createdAt: serverTimestamp(),
    dynamicUniverse: demoBuyIdeas.map((idea) => idea.ticker),
    openAiModel: "local-demo",
    status: "complete",
  });

  await Promise.all([
    ...demoHoldings.map((holding) => setDoc(doc(db, "users", userId, "holdings", holding.ticker), firestoreHolding(holding))),
    ...demoSignals.map((signal) => addDoc(collection(db, "users", userId, "analysisRuns", runRef.id, "actions"), firestoreSignal(signal))),
    ...demoBuyIdeas.map((idea) => addDoc(collection(db, "users", userId, "analysisRuns", runRef.id, "buyIdeas"), firestoreIdea(idea))),
    ...demoFactorIc.map((factor) => addDoc(collection(db, "users", userId, "factorIcLog"), firestoreFactor(factor))),
    ...demoSignals.map((signal) => addDoc(collection(db, "users", userId, "strategySignals"), firestoreSignal(signal))),
  ]);
}

export async function upsertInvestmentPlan(userId, plan) {
  requireFirebase();
  const runRef = await addDoc(collection(db, "users", userId, "analysisRuns"), {
    ...demoAnalysisRun,
    createdAt: serverTimestamp(),
    portfolioValue: demoAnalysisRun.portfolioValue,
    plainEnglishSummary: "Saved investment plan from the React strategy workspace.",
    status: "plan_saved",
  });
  await addDoc(collection(db, "users", userId, "analysisRuns", runRef.id, "investmentPlan"), {
    ...plan,
    createdAt: serverTimestamp(),
  });
}

export async function updateUserSettings(userId, settings) {
  requireFirebase();
  await setDoc(
    doc(db, "users", userId),
    {
      ...settings,
      updatedAt: serverTimestamp(),
    },
    { merge: true },
  );
}

export async function addBrokerConnection(userId, connection) {
  requireFirebase();
  const broker = connection.broker || "robinhood";
  const connectionRef = await addDoc(collection(db, "users", userId, "brokerConnections"), {
    broker,
    nickname: connection.nickname || (broker === "robinhood" ? "Robinhood Brokerage" : "Fidelity Brokerage"),
    status: connection.status || "needs_mfa",
    readOnly: true,
    secretRef: connection.secretRef || `secret-manager://${broker}/pending`,
    lastSyncAt: connection.lastSyncAt || null,
    lastError: connection.lastError || null,
    accountCount: connection.accountCount || 0,
    supportedActions: ["positions", "balances"],
    createdAt: serverTimestamp(),
  });
  await Promise.all(
    (connection.accounts || []).map((account) =>
      addDoc(collection(db, "users", userId, "brokerConnections", connectionRef.id, "accounts"), {
        ...account,
        lastSyncedAt: serverTimestamp(),
      }),
    ),
  );
}

export async function deleteBrokerConnection(userId, connectionId) {
  requireFirebase();
  const accountDocs = await getDocs(collection(db, "users", userId, "brokerConnections", connectionId, "accounts"));
  await Promise.all(accountDocs.docs.map((item) => deleteDoc(item.ref)));
  await deleteDoc(doc(db, "users", userId, "brokerConnections", connectionId));
}

export async function callBackendFunction(name, payload) {
  requireFirebase();
  const fn = httpsCallable(functions, name);
  return fn(payload);
}

function requireFirebase() {
  if (!firebaseReady || !app || !auth || !db) {
    throw new Error("Firebase is not configured. Set VITE_FIREBASE_* values in SignalPilot/.env.local.");
  }
}

function normalizeDoc(snapshot) {
  return { id: snapshot.id, ...snapshot.data() };
}

function firestoreErrorMessage(error) {
  if (error.code === "permission-denied") {
    return "Firestore rejected the request. Check Firestore rules for users/{userId} access.";
  }
  return error.message || "Firestore is not available.";
}

function normalizeHolding(row) {
  return {
    ticker: row.ticker,
    action: row.action || "HOLD",
    portfolioWeight: row.portfolioWeight ?? row.portfolio_weight ?? 0,
    marketValue: row.marketValue ?? row.market_value ?? 0,
    unrealizedGain: row.unrealizedGainPct ?? row.unrealizedGain ?? row.unrealized_gain ?? 0,
    finalScore: row.finalScore ?? row.score ?? 0,
    sector: row.sector || "Unknown",
  };
}

function normalizeAnalysis(row) {
  return {
    ...row,
    portfolioValue: row.portfolioValue ?? row.portfolio_value ?? 0,
    accountEquity: row.accountEquity ?? row.account_equity ?? 0,
    todayChange: row.todayChange ?? row.today_change ?? 0,
    todayChangePct: row.todayChangePct ?? row.today_change_pct ?? 0,
    plainEnglishSummary: row.plainEnglishSummary ?? row.plain_english_summary ?? "",
    riskSummary: row.riskSummary ?? row.risk_summary ?? "",
  };
}

function normalizeIdea(row) {
  return {
    ticker: row.ticker,
    name: row.name || row.ticker,
    score: row.score || 0,
    price: row.price || 0,
    reasons: row.reasons || [],
    modelDecision: row.modelDecision || row.model_decision || "Research / consider staged buy",
  };
}

function normalizeFactor(row) {
  return {
    factorName: row.factorName || row.factor_name,
    icValue: row.icValue ?? row.ic_value ?? 0,
    universeSize: row.universeSize ?? row.universe_size ?? 0,
    status: row.status || "Active",
  };
}

function normalizeSignal(row) {
  return {
    ticker: row.ticker,
    strategy: row.strategy || "Portfolio action engine",
    action: row.action || "HOLD",
    score: row.score ?? 0,
    status: row.status || "Active",
  };
}

function firestoreHolding(holding) {
  return {
    ticker: holding.ticker,
    broker: "demo",
    accountId: "demo-account",
    quantity: null,
    avgCost: null,
    price: null,
    marketValue: holding.marketValue,
    unrealizedGainPct: holding.unrealizedGain,
    portfolioWeight: holding.portfolioWeight,
    sector: holding.sector,
    action: holding.action,
    score: holding.finalScore,
    snapshotAt: serverTimestamp(),
  };
}

function firestoreSignal(signal) {
  return { ...signal, date: serverTimestamp(), createdAt: serverTimestamp() };
}

function firestoreIdea(idea) {
  return {
    ticker: idea.ticker,
    name: idea.name,
    score: idea.score,
    price: idea.price,
    reasons: idea.reasons,
    newsItems: [],
    modelDecision: idea.modelDecision,
    createdAt: serverTimestamp(),
  };
}

function firestoreFactor(factor) {
  return {
    date: serverTimestamp(),
    factorName: factor.factorName,
    icValue: factor.icValue,
    universeSize: factor.universeSize,
    status: factor.status,
  };
}

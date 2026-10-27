import { onAuthStateChanged, createUserWithEmailAndPassword, reload, sendEmailVerification, sendPasswordResetEmail, signInWithEmailAndPassword, signOut, User } from 'firebase/auth';
import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { Account, api, Patient } from './src/api';
import { auth } from './src/firebase';

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [emailVerified, setEmailVerified] = useState(false);
  const [account, setAccount] = useState<Account | null>(null);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [patientName, setPatientName] = useState('');
  const [linkCode, setLinkCode] = useState('');
  const [issuedCode, setIssuedCode] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => onAuthStateChanged(auth, async (nextUser) => {
    setUser(nextUser);
    setEmailVerified(Boolean(nextUser?.emailVerified));
    setAccount(null);
    setPatients([]);
    setMessage('');
    if (nextUser?.emailVerified) {
      try {
        const existing = await api<Account>(nextUser, '/v1/account');
        setAccount(existing);
        setPatients(await api<Patient[]>(nextUser, '/v1/patients'));
      } catch (error) {
        setMessage(error instanceof Error && error.message.includes('Create an account')
          ? 'Choose your account type to finish setup.'
          : error instanceof Error ? error.message : 'Could not load your account.');
      }
    }
  }), []);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setMessage('');
    try { await action(); }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Something went wrong.'); }
    finally { setBusy(false); }
  }

  async function createAccount(role: Account['role']) {
    if (!user) return;
    const created = await api<Account>(user, '/v1/account', {
      method: 'POST', body: JSON.stringify({ role, display_name: displayName.trim() }),
    });
    setAccount(created);
    setMessage('Your account is ready.');
  }

  async function addPatient() {
    if (!user) return;
    const patient = await api<Patient>(user, '/v1/patients', {
      method: 'POST', body: JSON.stringify({ display_name: patientName.trim() }),
    });
    setPatients((current) => [...current, patient]);
    setPatientName('');
  }

  async function issueLinkCode(patient: Patient) {
    if (!user) return;
    const result = await api<{ code: string; expires_in_seconds: number }>(
      user, `/v1/patients/${patient.id}/link-codes`, { method: 'POST' },
    );
    setIssuedCode(result.code);
    setMessage(`Share this code with the patient. It expires in ${Math.floor(result.expires_in_seconds / 60)} minutes.`);
  }

  async function revokeAccess(patient: Patient) {
    if (!user || !patient.relationship_id) return;
    await api<void>(user, `/v1/relationships/${patient.relationship_id}/revoke`, { method: 'POST' });
    setPatients((current) => current.filter((item) => item.id !== patient.id));
    setMessage(`Caregiver access for ${patient.display_name} has been revoked.`);
  }

  async function redeemCode() {
    if (!user) return;
    const patient = await api<Patient>(user, '/v1/link-codes/redeem', {
      method: 'POST', body: JSON.stringify({ code: linkCode.trim() }),
    });
    setPatients([patient]);
    setLinkCode('');
    setMessage('Your account is linked with your caregiver.');
  }

  async function refreshEmailVerification() {
    if (!user) return;
    await reload(user);
    const refreshedUser = auth.currentUser;
    if (!refreshedUser?.emailVerified) {
      setMessage('Your email is not verified yet. Open the verification link, then try again.');
      return;
    }
    setUser(refreshedUser);
    setEmailVerified(true);
    const existing = await api<Account>(refreshedUser, '/v1/account');
    setAccount(existing);
    setPatients(await api<Patient[]>(refreshedUser, '/v1/patients'));
  }

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <Text style={styles.brand}>ReMind</Text>
        <Text style={styles.heading}>A little help, every day</Text>
        {!user ? (
          <View style={styles.card}>
            <Text style={styles.section}>Sign in or create an account</Text>
            <TextInput accessibilityLabel="Email" autoCapitalize="none" keyboardType="email-address" style={styles.input} placeholder="Email" value={email} onChangeText={setEmail} />
            <TextInput accessibilityLabel="Password" secureTextEntry style={styles.input} placeholder="Password" value={password} onChangeText={setPassword} />
            <Button title="Sign in" disabled={busy} onPress={() => run(async () => { await signInWithEmailAndPassword(auth, email.trim(), password); })} />
            <Button title="Create account" disabled={busy} secondary onPress={() => run(async () => {
              const credential = await createUserWithEmailAndPassword(auth, email.trim(), password);
              await sendEmailVerification(credential.user);
              setMessage('We sent a verification link to your email.');
            })} />
            <Button title="Reset password" disabled={busy || !email.trim()} secondary onPress={() => run(async () => {
              await sendPasswordResetEmail(auth, email.trim());
              setMessage('Check your email for a password reset link.');
            })} />
          </View>
        ) : !emailVerified ? (
          <View style={styles.card}>
            <Text style={styles.section}>Verify your email</Text>
            <Text style={styles.copy}>Open the verification link sent to {user.email ?? 'your email'} before setting up ReMind.</Text>
            <Button title="Resend verification email" disabled={busy} onPress={() => run(async () => {
              await sendEmailVerification(user);
              setMessage('Verification email sent.');
            })} />
            <Button title="I verified my email" disabled={busy} secondary onPress={() => run(refreshEmailVerification)} />
            <Button title="Sign out" secondary onPress={() => run(() => signOut(auth))} />
          </View>
        ) : !account ? (
          <View style={styles.card}>
            <Text style={styles.section}>Set up your account</Text>
            <TextInput accessibilityLabel="Your name" style={styles.input} placeholder="Your name" value={displayName} onChangeText={setDisplayName} />
            <Button title="I’m a caregiver" disabled={busy || !displayName.trim()} onPress={() => run(() => createAccount('caregiver'))} />
            <Button title="I’m a patient" disabled={busy || !displayName.trim()} secondary onPress={() => run(() => createAccount('patient'))} />
            <Button title="Sign out" secondary onPress={() => run(() => signOut(auth))} />
          </View>
        ) : (
          <View style={styles.card}>
            <Text style={styles.section}>Hello, {account.display_name}</Text>
            {account.role === 'caregiver' ? (
              <>
                <Text style={styles.copy}>Create a patient profile, then share a one-time code so they can link their own account.</Text>
                <TextInput accessibilityLabel="Patient name" style={styles.input} placeholder="Patient name" value={patientName} onChangeText={setPatientName} />
                <Button title="Add patient profile" disabled={busy || !patientName.trim()} onPress={() => run(addPatient)} />
                {patients.map((patient) => (
                  <View key={patient.id} style={styles.patient}>
                    <Text style={styles.patientName}>{patient.display_name}</Text>
                    <Text style={styles.copy}>{patient.linked ? 'Account linked' : 'Not linked yet'}</Text>
                    {!patient.linked && <Button title="Create link code" disabled={busy} secondary onPress={() => run(() => issueLinkCode(patient))} />}
                    {patient.linked && patient.relationship_id && <Button title="Revoke caregiver access" disabled={busy} secondary onPress={() => run(() => revokeAccess(patient))} />}
                  </View>
                ))}
                {!!issuedCode && <Text selectable style={styles.code}>{issuedCode}</Text>}
              </>
            ) : (
              <>
                <Text style={styles.copy}>Enter the one-time code your caregiver shared with you.</Text>
                <TextInput accessibilityLabel="Caregiver link code" autoCapitalize="none" style={styles.input} placeholder="Link code" value={linkCode} onChangeText={setLinkCode} />
                <Button title="Link my account" disabled={busy || !linkCode.trim()} onPress={() => run(redeemCode)} />
                {patients.map((patient) => <Text key={patient.id} style={styles.patientName}>Linked profile: {patient.display_name}</Text>)}
              </>
            )}
            <Button title="Sign out" secondary onPress={() => run(() => signOut(auth))} />
          </View>
        )}
        {busy && <ActivityIndicator size="large" color="#254D68" />}
        {!!message && <Text accessibilityLiveRegion="polite" style={styles.message}>{message}</Text>}
        <Text style={styles.footer}>ReMind supports daily routines and memory recall. It does not replace professional care.</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

function Button({ title, onPress, disabled, secondary }: {
  title: string; onPress: () => void; disabled?: boolean; secondary?: boolean;
}) {
  return <Pressable accessibilityRole="button" onPress={onPress} disabled={disabled}
    style={[styles.button, secondary && styles.buttonSecondary, disabled && styles.disabled]}>
    <Text style={[styles.buttonText, secondary && styles.buttonTextSecondary]}>{title}</Text>
  </Pressable>;
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#F4F7F8' },
  container: { flexGrow: 1, justifyContent: 'center', padding: 24, paddingTop: 48, gap: 16 },
  brand: { color: '#254D68', fontSize: 22, fontWeight: '700' },
  heading: { color: '#1B2A33', fontSize: 30, fontWeight: '700', marginBottom: 8 },
  card: { backgroundColor: '#FFFFFF', borderRadius: 20, padding: 22, gap: 14, elevation: 2 },
  section: { fontSize: 22, fontWeight: '700', color: '#1B2A33' },
  copy: { color: '#43545F', fontSize: 17, lineHeight: 24 },
  input: { minHeight: 54, borderColor: '#AAB8C0', borderWidth: 1, borderRadius: 12, paddingHorizontal: 14, fontSize: 18, color: '#1B2A33' },
  button: { minHeight: 54, borderRadius: 12, backgroundColor: '#254D68', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16 },
  buttonSecondary: { backgroundColor: '#E6EFF3', borderWidth: 1, borderColor: '#A6C0CD' },
  buttonText: { color: '#FFFFFF', fontWeight: '700', fontSize: 17 },
  buttonTextSecondary: { color: '#254D68' },
  disabled: { opacity: 0.5 },
  patient: { borderTopWidth: 1, borderColor: '#E2E8EB', paddingTop: 14, gap: 8 },
  patientName: { fontWeight: '700', color: '#1B2A33', fontSize: 18 },
  code: { fontSize: 16, fontWeight: '700', color: '#163C58', backgroundColor: '#EAF3F7', padding: 14, borderRadius: 10 },
  message: { color: '#254D68', fontSize: 16, lineHeight: 22 },
  footer: { color: '#61717A', fontSize: 14, lineHeight: 20, marginTop: 8 },
});

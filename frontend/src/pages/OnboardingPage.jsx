import { useState, useMemo, useCallback } from 'react';
import { useApp } from '../context/AppContext.jsx';
import {
  OnboardingHeader, OnboardingFooter, WelcomeIntro, ProviderPicker,
  SetupGuide, ConnectionForm, ConnectionTester, Callout, Icons,
} from '../components/index.js';

const STEPS = ['Welcome', 'Connect', 'Confirm'];
const MODEL_NAMES = {
  'claude-haiku-4-5': 'Claude Haiku 4.5',
  'claude-sonnet-4-6': 'Claude Sonnet 4.6',
  'claude-opus-4-8': 'Claude Opus 4.8',
};

// First-run setup wizard. Walks the user through connecting an AI model - either
// Anthropic's hosted Claude or a local Anthropic-compatible server - then tests
// and saves it. Skippable: "Continue on mock content" closes it and the app runs
// on mock data (the top-bar pill reopens this anytime). Composed entirely from
// the component library.
export default function OnboardingPage() {
  const { llm, saveLLM, testLLM, closeOnboarding, toast } = useApp();

  const [step, setStep] = useState(0);
  const [provider, setProvider] = useState(llm?.provider || 'anthropic');
  // Keep a working draft per provider so switching does not lose what was typed.
  const [forms, setForms] = useState(() => ({
    anthropic: { model: llm?.anthropic?.model || llm?.default_model || 'claude-haiku-4-5', apiKey: '', baseUrl: '' },
    local: { model: llm?.local?.model || '', apiKey: '', baseUrl: llm?.local?.base_url || '' },
  }));
  const [test, setTest] = useState({ status: 'idle', message: '' });
  const [saving, setSaving] = useState(false);

  const form = forms[provider];
  const hasSavedKey = !!llm?.[provider]?.has_api_key;
  const models = useMemo(() => llm?.models || [], [llm]);

  const setField = useCallback((name, value) => {
    setForms((f) => ({ ...f, [provider]: { ...f[provider], [name]: value } }));
    setTest({ status: 'idle', message: '' });
  }, [provider]);

  const changeProvider = useCallback((p) => {
    setProvider(p);
    setTest({ status: 'idle', message: '' });
  }, []);

  // Enough to attempt a connection: a key (or a saved one) for Anthropic, a base
  // URL and model for local.
  const canConnect = provider === 'local'
    ? (!!form.baseUrl.trim() && !!form.model.trim())
    : (!!form.apiKey.trim() || hasSavedKey);

  const patch = useCallback(() => ({
    provider,
    model: form.model,
    api_key: form.apiKey,
    base_url: form.baseUrl,
  }), [provider, form]);

  const runTest = useCallback(async () => {
    setTest({ status: 'testing', message: '' });
    try {
      const res = await testLLM(patch());
      setTest({ status: res.ok ? 'ok' : 'error', message: res.message || (res.ok ? 'Connected.' : 'Could not connect.') });
    } catch (e) {
      setTest({ status: 'error', message: e.message });
    }
  }, [testLLM, patch]);

  const save = useCallback(async () => {
    setSaving(true);
    try {
      const body = {
        provider,
        enabled: true,
        [provider]: provider === 'anthropic'
          ? { model: form.model, api_key: form.apiKey }
          : { model: form.model, base_url: form.baseUrl, api_key: form.apiKey },
      };
      await saveLLM(body);
      setStep(2);
    } catch (e) {
      toast('Could not save connection: ' + e.message);
    } finally {
      setSaving(false);
    }
  }, [provider, form, saveLLM, toast]);

  return (
    <div className="onb">
      <OnboardingHeader steps={STEPS} current={step} />

      <div className="onb-body">
        <div className="onb-inner">
          {step === 0 && <WelcomeIntro />}

          {step === 1 && (
            <div className="onb-connect">
              <ProviderPicker value={provider} onChange={changeProvider} />
              <div className="onb-cols">
                <SetupGuide provider={provider} />
                <div className="onb-form">
                  <ConnectionForm
                    provider={provider}
                    value={form}
                    onField={setField}
                    models={models}
                    hasSavedKey={hasSavedKey}
                  />
                  <ConnectionTester
                    status={test.status}
                    message={test.message}
                    onTest={runTest}
                    disabled={!canConnect}
                  />
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="onb-confirm">
              {llm?.ready ? (
                <Callout tone="success" title="You are connected">
                  Dynasty+ will generate with {MODEL_NAMES[llm.model] || llm.model}
                  {llm.provider === 'local' ? ' on your local server' : ''}. Every new week is written live
                  from your dynasty.
                </Callout>
              ) : (
                <Callout tone="warn" title="Saved, but generation is off">
                  The connection was saved but is not active yet. The app will run on mock content until it is
                  ready. Reopen setup from the top bar to finish.
                </Callout>
              )}
            </div>
          )}
        </div>
      </div>

      {step === 0 && (
        <OnboardingFooter onPrimary={() => setStep(1)} primaryLabel="Get started" />
      )}
      {step === 1 && (
        <OnboardingFooter
          onBack={() => setStep(0)}
          onPrimary={save}
          primaryLabel="Save and connect"
          primaryDisabled={!canConnect}
          primarySpinning={saving}
          hint={test.status === 'ok' ? 'Test passed' : undefined}
        />
      )}
      {step === 2 && (
        <OnboardingFooter onPrimary={closeOnboarding} primaryLabel="Enter your dynasty" primaryIcon={<Icons.PlayIcon />} />
      )}
    </div>
  );
}

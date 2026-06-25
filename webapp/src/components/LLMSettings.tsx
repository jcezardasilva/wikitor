import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';
import type { LLMProvider } from '../types';

const PROVIDERS: { value: LLMProvider; label: string }[] = [
  { value: 'ollama', label: 'Ollama (local)' },
  { value: 'openai_compatible', label: 'OpenAI-compatible (Groq, OpenRouter, …)' },
];

// Painel de configuração do provedor de LLM ativo (global, persistido no backend).
export function LLMSettings({ onChanged }: { onChanged?: () => void }) {
  const [provider, setProvider] = useState<LLMProvider>('ollama');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState(''); // vazio = manter a chave atual
  const [keyMask, setKeyMask] = useState<string | null>(null);
  const [model, setModel] = useState('');
  const [models, setModels] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [busca, setBusca] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    try {
      const s = await api.getLlmSettings();
      setProvider(s.provider);
      setBaseUrl(s.base_url);
      setModel(s.model);
      setKeyMask(s.api_key_masked);
    } catch (e) {
      setErro(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const buscarModelos = async () => {
    setBusca(true);
    setErro(null);
    try {
      const r = await api.fetchModels(provider, baseUrl, apiKey || undefined);
      setModels(r.models);
      if (r.models.length && !r.models.includes(model)) setModel(r.models[0]);
    } catch (e) {
      setErro(String(e));
    } finally {
      setBusca(false);
    }
  };

  const salvar = async () => {
    setErro(null);
    setOk(null);
    try {
      const s = await api.saveLlmSettings({
        provider,
        base_url: baseUrl,
        model,
        api_key: apiKey || undefined, // vazio = mantém a atual
      });
      setKeyMask(s.api_key_masked);
      setApiKey('');
      setOk('Configuração salva.');
      onChanged?.();
    } catch (e) {
      setErro(String(e));
    }
  };

  if (loading) {
    return (
      <div className="panel">
        <div className="muted">Carregando configuração…</div>
      </div>
    );
  }

  const isOpenAI = provider === 'openai_compatible';
  const keyPlaceholder = keyMask ? `atual: ${keyMask} (deixe vazio p/ manter)` : 'sk-…';

  return (
    <div className="panel">
      <h2>Provedor de LLM</h2>
      <p className="muted">
        Define o provedor e o modelo usados em todo o Wikitor. A chave é guardada no servidor e
        nunca é exibida de volta.
      </p>

      <label className="field">
        <span className="muted">Provedor</span>
        <select value={provider} onChange={(e) => setProvider(e.target.value as LLMProvider)}>
          {PROVIDERS.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
      </label>

      <label className="field">
        <span className="muted">Base URL</span>
        <input
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          placeholder={isOpenAI ? 'https://api.groq.com/openai' : 'http://localhost:11434'}
        />
      </label>

      {isOpenAI && (
        <label className="field">
          <span className="muted">API key</span>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={keyPlaceholder}
          />
        </label>
      )}

      <div className="field-row">
        <button onClick={buscarModelos} disabled={busca || !baseUrl}>
          {busca ? 'Buscando…' : 'Buscar modelos'}
        </button>
      </div>

      <label className="field">
        <span className="muted">Modelo</span>
        <input
          list="llm-models"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          placeholder='clique em "Buscar modelos" ou digite o nome'
        />
        <datalist id="llm-models">
          {models.map((m) => (
            <option key={m} value={m} />
          ))}
        </datalist>
      </label>

      {erro && <div className="error">{erro}</div>}
      {ok && <div className="muted">{ok}</div>}

      <div className="field-row">
        <button className="primary" onClick={salvar} disabled={!baseUrl || !model}>
          Salvar
        </button>
      </div>
    </div>
  );
}

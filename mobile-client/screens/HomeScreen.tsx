import React, { useEffect, useState } from 'react';
import StatusMessage from '../components/StatusMessage';
import { apiGet } from '../services/api';

export default function HomeScreen() {
  const [status, setStatus] = useState<'loading' | 'ok' | 'error'>('loading');

  useEffect(() => {
    apiGet('/api/ping')
      .then(() => setStatus('ok'))
      .catch(() => setStatus('error'));
  }, []);

  return <StatusMessage status={status} />;
}

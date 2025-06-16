import React, { useEffect, useState } from 'react';
import { Button, View } from 'react-native';
import StatusMessage from '../components/StatusMessage';
import { apiGet } from '../services/api';
import { useNavigation } from '@react-navigation/native';

export default function HomeScreen() {
  const [status, setStatus] = useState<'loading' | 'ok' | 'error'>('loading');
  const navigation = useNavigation();

  useEffect(() => {
    apiGet('/api/ping')
      .then(() => setStatus('ok'))
      .catch(() => setStatus('error'));
  }, []);

  return (
    <View style={{ flex: 1 }}>
      <StatusMessage status={status} />
      <Button title="Profile" onPress={() => navigation.navigate('Profile' as never)} />
    </View>
  );
}

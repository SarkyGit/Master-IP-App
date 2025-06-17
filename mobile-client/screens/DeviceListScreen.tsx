import React, { useCallback, useEffect, useState } from 'react';
import {
  View,
  Text,
  FlatList,
  ActivityIndicator,
  StyleSheet,
  RefreshControl,
  TextInput,
} from 'react-native';
import { fetchDevices, Device } from '../services/devices';

export default function DeviceListScreen() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [search, setSearch] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchDevices();
      setDevices(data);
    } catch (err) {
      console.error('Device fetch failed', err);
      setError('Failed to load devices');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onRefresh = async () => {
    setRefreshing(true);
    try {
      const data = await fetchDevices();
      setDevices(data);
    } catch (err) {
      console.error('Device fetch failed', err);
      setError('Failed to load devices');
    } finally {
      setRefreshing(false);
    }
  };

  const filtered = devices.filter((d) =>
    d.hostname.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.error}>{error}</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <TextInput
        style={styles.search}
        placeholder="Search"
        value={search}
        onChangeText={setSearch}
      />
      <FlatList
        data={filtered}
        keyExtractor={(item) => String(item.id)}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        renderItem={({ item }) => (
          <View style={styles.card}>
            <Text style={styles.host}>{item.hostname}</Text>
            <Text style={styles.detail}>{item.ip}</Text>
            {item.device_type && (
              <Text style={styles.detail}>{item.device_type}</Text>
            )}
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
    backgroundColor: '#000',
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#000',
  },
  card: {
    padding: 12,
    marginBottom: 8,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#14b8a6',
    backgroundColor: '#1e293b',
  },
  host: {
    fontWeight: 'bold',
    marginBottom: 4,
    color: '#f97316',
  },
  detail: {
    color: '#f1f5f9',
  },
  search: {
    borderWidth: 1,
    borderColor: '#14b8a6',
    backgroundColor: '#1f2937',
    color: '#f9fafb',
    padding: 8,
    marginBottom: 12,
    borderRadius: 4,
  },
  error: {
    color: '#ec4899',
  },
});

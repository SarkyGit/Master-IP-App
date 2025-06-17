import React, { useState, useContext } from 'react';
import { View, TextInput, Button, StyleSheet, Text } from 'react-native';
import AuthContext from '../context/AuthContext';

export default function LoginScreen() {
  const { login } = useContext(AuthContext);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async () => {
    try {
      setError(null);
      await login(email, password);
    } catch (err) {
      setError('Invalid credentials');
    }
  };

  return (
    <View style={styles.container}>
      <TextInput
        style={styles.input}
        placeholder="Email"
        autoCapitalize="none"
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />
      {error && <Text style={styles.error}>{error}</Text>}
      <Button title="Login" color="#f97316" onPress={handleLogin} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: 16,
    backgroundColor: '#000',
  },
  input: {
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
    marginBottom: 12,
    textAlign: 'center',
  },
});

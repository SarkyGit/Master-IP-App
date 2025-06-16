import React, { createContext, useState, useEffect, ReactNode } from 'react';
import * as SecureStore from 'expo-secure-store';
import { apiPost, apiGet, setAuthToken } from '../services/api';

interface User {
  email: string;
  role: string;
}

interface AuthContextProps {
  token: string | null;
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  loading: boolean;
}

const AuthContext = createContext<AuthContextProps>({
  token: null,
  user: null,
  // eslint-disable-next-line @typescript-eslint/no-empty-function
  login: async () => {},
  // eslint-disable-next-line @typescript-eslint/no-empty-function
  logout: async () => {},
  loading: true,
});

const TOKEN_KEY = 'accessToken';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const storedToken = await SecureStore.getItemAsync(TOKEN_KEY);
      if (storedToken) {
        setAuthToken(storedToken);
        setToken(storedToken);
        try {
          const me = await apiGet('/auth/me');
          setUser(me);
        } catch {
          await SecureStore.deleteItemAsync(TOKEN_KEY);
          setToken(null);
        }
      }
      setLoading(false);
    })();
  }, []);

  const login = async (email: string, password: string) => {
    const res = await apiPost('/auth/token', { email, password });
    const access = res.access_token as string;
    await SecureStore.setItemAsync(TOKEN_KEY, access);
    setAuthToken(access);
    setToken(access);
    const me = await apiGet('/auth/me');
    setUser(me);
  };

  const logout = async () => {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
    setAuthToken(null);
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ token, user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export default AuthContext;

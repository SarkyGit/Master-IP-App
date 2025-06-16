import React, { useContext } from 'react';
import { View, Text, Button, StyleSheet } from 'react-native';
import AuthContext from '../context/AuthContext';

export default function ProfileScreen() {
  const { user, logout } = useContext(AuthContext);

  return (
    <View style={styles.container}>
      <Text style={styles.text}>Email: {user?.email}</Text>
      <Text style={styles.text}>Role: {user?.role}</Text>
      <Button title="Logout" onPress={logout} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
  },
  text: {
    marginBottom: 12,
  },
});

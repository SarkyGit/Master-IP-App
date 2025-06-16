import React from 'react';
import { Text, StyleSheet, View } from 'react-native';

type Props = {
  status: 'loading' | 'ok' | 'error';
};

export default function StatusMessage({ status }: Props) {
  let message = 'Checking server...';
  if (status === 'ok') {
    message = 'Server online';
  } else if (status === 'error') {
    message = 'Server unreachable';
  }
  return (
    <View style={styles.center}>
      <Text>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
});

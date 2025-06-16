import React, {useEffect, useState} from 'react';
import {SafeAreaView, Text, FlatList} from 'react-native';

export default function App() {
  const [devices, setDevices] = useState([]);
  useEffect(() => {
    fetch('http://localhost:8000/api/v1/devices')
      .then(res => res.json())
      .then(data => setDevices(data))
      .catch(() => {});
  }, []);
  return (
    <SafeAreaView>
      <FlatList
        data={devices}
        keyExtractor={item => String(item.id)}
        renderItem={({item}) => <Text>{item.hostname}</Text>}
      />
    </SafeAreaView>
  );
}

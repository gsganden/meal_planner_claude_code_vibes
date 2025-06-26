// Debug script to test recipe creation
// Run this in the browser console while logged in

const testRecipeCreation = async () => {
  try {
    // Check if we have a token
    const token = localStorage.getItem('access_token');
    console.log('Token exists:', !!token);
    
    // Make the request
    const response = await fetch('/v1/recipes', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        title: '',
        yield: '1 serving',
        ingredients: [],
        steps: []
      })
    });
    
    console.log('Response status:', response.status);
    const data = await response.json();
    console.log('Response data:', data);
    
    if (!response.ok) {
      console.error('Error response:', data);
    }
    
    return data;
  } catch (error) {
    console.error('Request failed:', error);
  }
};

// Also check axios configuration
console.log('Axios defaults:', axios.defaults);
console.log('Axios interceptors:', axios.interceptors);

testRecipeCreation();
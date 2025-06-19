(function(){
  const IP_RE = /^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
  function normalize(val){
    return val.split('.').map(o=>String(Number(o))).join('.');
  }
  function setupInput(input){
    const error = input.parentElement.querySelector('.ip-error');
    function show(msg){
      if(error){ error.textContent = msg; error.classList.remove('hidden'); }
      input.classList.add('border-red-500');
    }
    function clear(){
      if(error) error.classList.add('hidden');
      input.classList.remove('border-red-500');
      input.setCustomValidity('');
    }
    input.addEventListener('input', ()=>{
      const cleaned = input.value.replace(/[^0-9.]/g,'');
      if(cleaned !== input.value) input.value = cleaned;
    });
    input.addEventListener('blur', ()=>{
      const val = input.value.trim();
      if(!val){ clear(); return; }
      if(IP_RE.test(val)){
        input.value = normalize(val);
        clear();
      }else{
        show('Invalid IP address');
        input.setCustomValidity('Invalid IP address');
      }
    });
  }
  document.addEventListener('DOMContentLoaded', ()=>{
    document.querySelectorAll('input.ip-input').forEach(setupInput);
  });
})();

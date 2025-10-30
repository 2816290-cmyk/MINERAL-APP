document.addEventListener("DOMContentLoaded", function(){
  const pw = document.getElementById("password");
  const strength = document.getElementById("strength");
  if (!pw || !strength) return;

  pw.addEventListener("input", () => {
    const val = pw.value;
    let score = 0;
    if (val.length >= 8) score++;
    if (/[A-Z]/.test(val)) score++;
    if (/[a-z]/.test(val)) score++;
    if (/[0-9]/.test(val)) score++;
    if (/[^A-Za-z0-9]/.test(val)) score++;
    const labels = ["Very weak","Weak","Okay","Good","Strong","Very strong"];
    strength.innerHTML = `<div class="progress">
      <div class="progress-bar" role="progressbar" style="width:${score*20}%">${labels[score]}</div>
    </div>`;
  });
});

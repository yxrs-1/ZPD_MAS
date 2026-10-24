var account = document.querySelector(".teacher-nav .account");
var card = document.querySelector(".teacher-nav .account-card");
if (account && card) {
  account.addEventListener("click", function () {
    card.classList.toggle("open");
  });
}

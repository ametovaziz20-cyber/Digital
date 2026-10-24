// Сценарии работают только на тех страницах, где есть нужные элементы.
const message = document.getElementById('message');
if (message) {
  setTimeout(function () { message.style.display = 'none'; }, 3000);
}

const orderButton = document.querySelector('.my_orders');
const orderList = document.querySelector('.list_orders');
const orderArrow = document.querySelector('.errow_down');
if (orderButton && orderList) {
  orderButton.addEventListener('click', function () {
    orderList.classList.toggle('active');
    if (orderArrow) orderArrow.classList.toggle('active');
  });
}

const reviewButton = document.querySelector('.answer-review');
const reviewForm = document.querySelector('.answer-form');
if (reviewButton && reviewForm) {
  reviewButton.addEventListener('click', function () {
    reviewForm.classList.toggle('active_review');
  });
}

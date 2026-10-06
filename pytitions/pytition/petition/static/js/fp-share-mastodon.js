/* Configuration of vendor/msb/js/mastodon.js (Mastodon share button), loaded just before it. */
var msbConfig = {
  openModal: function () {
    $('#MastodonModal').modal('show');
  },
  closeModal: function () {
    $('#MastodonModal').modal('hide');
  },
  addressFieldSelector: '#msb-address',
  buttonModalSelector: '#msb-share',
  memorizeFieldId: 'msb-memorize-instance',
};

$('.modal').on('shown.bs.modal', function () {
  $('#msb-address').focus();
});

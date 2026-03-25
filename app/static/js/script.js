var currentPath;

$(document).ready(function() {
    currentPath = window.location.pathname;
    var wishRegex = /((?<=\d+)\/)?wish\/\d+/;

    if (wishRegex.test(currentPath)) {
        currentPath = currentPath.replace(wishRegex, '');
    }


    // -----------------------------------------------------------------
    // Click handlers
    // -----------------------------------------------------------------
    $(".new-wish-button").click(openNewWish);
    $(".user-lists-button").on("click",openListsModal);
    $(".nav-checkbox").click(toggleHamburger);
    $(".sidebar-nav .order-by").click(order_users_by);
    $(".edit-item").click(editListItem);
    $("#add-new-key").click(function() {window.location.href = "dashboard/add-security-key"})
    $(".logout-button").click(logoutUser);
    $(document).on('click', '.list-filter-pill', filterWishesByList);
});

$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", csrf_token);
        }
    }
});

function ajaxCallCsrf(route, data, type="POST", callback) {
    return $.ajax({
        url: route,
        type: type, // or "GET" or any other HTTP method you want to use
        data: data,
        success: callback
    });
}

function hideModalAndUpdateUrl() {
    modal.style.display = "none";
    // Restore the original URL
    history.pushState({}, '', currentPath);
}

function loadListToForm(event) {
    event.preventDefault()
    $(".selected-item").removeClass("selected-item");
    $(this).parent().addClass("selected-item");
    var list_id = $(this).data("list-id");
    if (list_id == 0) {
        $("#list_form #title").val("")
        $("#list_form #expires_at").val("");
        $("#list_form :radio[name='private'][value='Nei']").prop('checked', true);
    }
    else {
        $.get("/api/wish-list/" + list_id, function(data) {
            $("#list_form #title").val(data['title'])
            $("#list_form #expires_at").val(data['expires_at']);
            if (data['private']) {
                $("#list_form :radio[name='private'][value='Ja']").prop('checked', true);
            }
            else {
                $("#list_form :radio[name='private'][value='Nei']").prop('checked', true);
            }
        })
    }
}

function submitListForm(event){
    event.preventDefault();
    var template = $("input[name='template']:checked").val();
    var confirmation_delay = 2000;
    var payload = { template: template };
    // Custom lists require a user-supplied title and expiry date.
    // Christmas/birthday auto-generate their title on the server.
    if (template === 'custom') {
        payload.title = $("#list_form #title").val().trim();
        payload.expires_at = $("#list_form #expires_at").val();
    }
    $('#list-form-error').hide();
    $('#list-submit i.fa-spinner').css('display', 'inline-block');
    $('#list-submit span').hide();
    $.ajax({
        url: '/api/lists',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(payload),
    }).done(function() {        
        $('#list-submit i.fa-spinner').hide();
        $('#list-submit i.fa-check').css('display', 'inline-block')
        // Reload page so filter pills update with the newly created list.
        setTimeout(function() { window.location.reload(); }, confirmation_delay);
    }).fail(function(xhr) {
        $('#list-submit i.fa-spinner').hide();
        $('#list-submit span').show();
        var msg = xhr.responseJSON && xhr.responseJSON.error
            ? xhr.responseJSON.error
            : 'Det oppstod en feil.';
        $('#list-form-error').text(msg).show();
    });
}

// Show/hide the date picker and title field based on which template pill is active.
// Christmas and birthday auto-generate a title, so the title field is hidden.
// Only custom lists expose the date picker.
function toggleListDatePicker() {
    var template = $("input[name='template']:checked").val();
    var isNamed = template === 'christmas' || template === 'birthday';
    var isCustom = template === 'custom';
    $('#list-title-wrapper').toggle(!isNamed);
    $('#auto-title-hint').toggle(isNamed);
    $('#custom-date-wrapper').toggle(isCustom);
}

function updateCredentialName(entry_id, label, callback) {
    $.post("/webauthn/update", {
        entry_id: entry_id,
        label:label
    }, function () {
        callback();
    })
}

function deleteCredential(entry_id, clicked, parent) {
    $.ajax({
        url: "/webauthn/delete",
        type: "DELETE", // or "GET" or any other HTTP method you want to use
        data: {
            entry_id: entry_id
        }
    })
        .done(function () {
            clicked.trigger("click");
            parent.remove();
            removeAlertModal();
            if (!$("tbody").children().length) {
                location.reload();
            }
        })
        .fail(function() {
            removeAlertModal()
            showAlertModal({
                title: "Oisann",
                message: "Det oppstod en feil, prøv på nytt."
            })
        })
}

function createAlertModal(message, title, img, img_alt, confirm=false, close_all=false) {
    // Create a new div element with the specified classes
    var confirmActionDiv = $('<div>').addClass('confirm-action content');

    // Check if 'title' variable is provided and create an h2 element
    if (title) {
        var titleElement = $('<h2>').text(title);
        confirmActionDiv.append(titleElement);
    }

    // Check conditions and create either an image or a paragraph element
    if (img) {
        var imgElement = $('<img>').attr('src', img).attr('alt', img_alt);
        confirmActionDiv.append(imgElement);
    } else if (message) {
        var messageElement = $('<p>').text(message);
        confirmActionDiv.append(messageElement);
    }

    // Create a div element with class 'actions'
    var actionsDiv = $('<div>').addClass('actions');

    // Check the 'buttons' variable and add appropriate buttons
    if (confirm) {
        var sendButton = $('<button>').addClass('button send').text('Send');
        var cancelButton = $('<button>').addClass('button cancel').attr("id", "close-button").text('Avbryt');
        actionsDiv.append(sendButton, cancelButton);
    } else {
        var closeButton = $('<button>')
            .addClass('button cancel')
            .attr("id", "close-button")
            .text('Lukk');
        if (close_all) {
            closeButton.attr('data-close-all', 'true');
        }
        actionsDiv.append(closeButton);
    }

    // Append the 'actions' div to the main confirmActionDiv
    confirmActionDiv.append(actionsDiv);

    // Append the confirmActionDiv to an element with class 'container'
    $(".confirm-action.modal-content").append(confirmActionDiv);
}

function showAlertModal(options) {
    var title = options.title;
    var img = options.img;
    var img_alt = options.img_alt;
    var message = options.message;
    var close_all = options.close_all;
    var send_callback = options.send_callback;
    var confirm = !!options.send_callback;
    createAlertModal(message, title, img, img_alt, confirm, close_all);
    $("#modal-confirm").css("display", "flex");
    if (confirm) {
        $(".button.send").on("click", send_callback);
    }

    var confirmModal = document.getElementById("modal-confirm");
    var cancelButton = document.getElementById("close-button");
    window.addEventListener("click", function(event) {
        if (event.target === confirmModal || event.target === cancelButton) {
            removeAlertModal()
        }})
}

function removeAlertModal() {
    $(".confirm-action.content").remove();
    $("#modal-confirm").hide();
}
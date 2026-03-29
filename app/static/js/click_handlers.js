function openListsModal() {
    // Set modal content
    loadModal("/api/wish/lists").then(function () {
        $(".wish-list-item").click(loadListToForm);
        // Update visibility of title/date fields when a template pill is selected.
        $("input[name='template']").on('change', toggleListDatePicker);
        toggleListDatePicker();
        $("#list_form").submit(submitListForm);
    });
}

function toggleHamburger() {
    if ($(".nav-checkbox").is(":checked")) {
        $("main").hide(0, function () {
            $(".container").css("grid-template-columns", "1fr 0 0");
            $(".nav-toggle-item").toggle();
        })
    }
    else {
        $(".nav-toggle-item").toggle(0, function () {
            $(".container").css("grid-template-columns", "0 1fr 1fr");
            $("main").show(0)
        })
    }
}

function order_users_by() {
    $.post("/api/settings/order_by", { "order_by": $(".order-by.hidden").data("order-by") }, function (data) {
        var ul = $('.sidebar-nav ul.users');
        ul.empty()
        $.each(data, function (index, user) {
            var li = $('<li>');
            var a = $('<a>').attr('href', user.path).text(user.first_name);
            li.append(a);
            ul.append(li);
        });
        $(".sidebar-nav .order-by.toggle").toggleClass('hidden');
    })
}

function editListItem() {
    let clicked = $(this)
    var parent = clicked.parent();
    var siblings = clicked.siblings();
    parent.toggleClass("editing");

    if (parent.hasClass("editing")) {
        let key_name = clicked.siblings().first().text();
        let entry_id = clicked.data("entry-id");
        clicked.find("i").css("transform", "rotate(90deg)");
        siblings.addBack().css("border-bottom", "none");
        var input = $($(document.createElement('input')))
            .attr("type", "text")
            .val(key_name);
        siblings.first().empty().append(input);
        // Create the <tr> element with class 'edit-item'
        var $row = $($(document.createElement('tr')))
            .addClass('edit-item');

        // Create the first <td> element with a delete button
        var $td1 = $($(document.createElement('td')))
            .attr("colspan", "4");
        var $innerDiv = $($(document.createElement('div')));
        $td1.append($innerDiv);
        var $deleteButton = $($(document.createElement('button')))
            .addClass('delete')
            .text('Slett')
            .on("click", function () {
                showAlertModal({
                    title: "Slette nøkkel?",
                    message: "Sikkerhetsnøkkelen vil bli slettet for godt.",
                    send_callback: function () {
                        deleteCredential(entry_id, clicked, parent)
                    }
                })
            });
        $innerDiv.append($deleteButton);
        var $buttonsDiv = $($(document.createElement('div')));
        var $cancelButton = $($(document.createElement('button')))
            .addClass('cancel')
            .text('Avbryt')
            .on("click", function () {
                clicked.trigger("click")
            });

        var $saveButton = $($(document.createElement('button')))
            .addClass('save btn btn-accent')
            .text('Lagre')
            .on("click", function () {
                updateCredentialName(
                    entry_id,
                    siblings.first().children("input").val(),
                    clicked.trigger("click")
                )
            });
        $buttonsDiv.append($cancelButton, $saveButton);
        $innerDiv.append($buttonsDiv);

        // Append the <td> elements to the <tr> element
        $row.append($td1);

        // Append the <tr> element to the DOM (assuming you have a table with id 'myTable')
        parent.after($row);
    }
    else {
        let key_name = siblings.first().children("input").val()
        clicked.find("i").css("transform", "");
        siblings.addBack().css("border-bottom", "");
        siblings.first().empty().text(key_name);
        parent.next(".edit-item").remove();
    }
}

function logoutUser() {
    ajaxCallCsrf('/api/logout', { csrf_token: $("#csrf_token").val() }).then(function () {
        window.location.href = '/';
    });
}

function filterWishesByList() {
    // Filter visible wish cards by list when a list label pill is clicked.
    // 'all' resets to showing every wish; any other value narrows by list_id.
    $('.list-filter-pill').removeClass('active');
    $(this).addClass('active');
    var listId = $(this).data('list-id');
    var wishes = user_wishes || [];
    var toShow = listId === 'all'
        ? wishes
        : $.grep(wishes, function (w) { return w.list_id == listId; });
    calculateColumnsAndAppendWishes(toShow);
}

function openNewWish() {
    loadModal("/api/wish/new");
}
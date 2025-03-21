function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}



document.addEventListener('DOMContentLoaded', () => {
    const buttons = document.querySelectorAll('#draggableButton')
    //const button = document.getElementById('draggableButton');
    const droppableRows = document.querySelectorAll('.droppable-row');
    const powerupmodal = new bootstrap.Modal(document.getElementById('powerupmodal'), {
      keyboard: true
    })
    const modaltext = document.getElementById('powerup-modal-text')
    const powerupsavebtn = document.getElementById('powerup_save')
    // let currentRow = null;

    buttons.forEach((button) => {
      button.addEventListener('dragstart', (event) => {
        event.dataTransfer.setData('text/plain', button.getAttribute('data-button-name'));
    })
  });

    powerupsavebtn.addEventListener('click', (event) => {
         // event.dataTransfer.setData('text/plain', button.getAttribute('data-button-name'));
        const content  = document.getElementById('powerup-modal-text').textContent;
        //const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        var csrf_token = getCookie('csrftoken');
        console.log("Tushar event triggered"+content)
      powerupmodal.hide();
      fetch('/update_powerups/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
            'X-CSRFToken': csrf_token ,
        },
        body: JSON.stringify({ content }),
      })
      .then(response => response.text())
      .then(data => {
        window.location.reload();
      })
      .catch(error => console.error('Error:', error));

     });

    droppableRows.forEach((row) => {
      row.addEventListener('dragenter', () => {
        row.classList.add('highlight');
      });

      row.addEventListener('dragleave', () => {
        row.classList.remove('highlight');
      });

      row.addEventListener('dragover', (e) => {
        e.preventDefault();
      });

      row.addEventListener('drop', (e) => {
        e.preventDefault();
        row.classList.remove('highlight');
        const buttonName = e.dataTransfer.getData('text/plain');
        const rowName = row.getAttribute('data-row-name');
        modaltext.textContent = `This will apply ${buttonName} Power Up on Match number ${rowName} ! Are you sure?`;
        console.log("Tushar modal is now displayed");
        powerupmodal.show();

        //alert(`Are you sure that you want to apply ${buttonName} powerup on match number ${rowName}`);
      });
    });

});

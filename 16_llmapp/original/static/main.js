window.onload = function()
{
  // Get the chat box
  const chatBox = document.getElementById('chat-box') ;

  // Set the scroll position of the chat box to the bottom
  chatBox.scrollTop = chatBox.scrollHeight ;

  // Submit the form with Ctrl + Enter
  const form = document.getElementById('chat-form') ;
  const textarea = document.getElementById('user-input') ;

  textarea.addEventListener('keydown', function(event)
  {
      const submitButton = document.getElementById('submit-button') ;
      const userInput = document.getElementById('user-input') ;

      // Don't add empty line
      if ( event.key === 'Enter' && userInput.value.trim() === '' )
      {
          userInput.value = '' ;
          event.preventDefault();  // Prevent the default action (like a new line)
      }
      else
      // If only the Enter key is pressed (not with Shift, Ctrl, or Alt)
      if ( event.key === 'Enter' && !event.shiftKey && !submitButton.disabled
           && userInput.value.trim() != '' )
      {
          event.preventDefault();  // Prevent the default action (like a new line)
          form.submit();  // Submit the form
      }
  }) ;
}

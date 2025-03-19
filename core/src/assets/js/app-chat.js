/**
 * App Chat
 */

'use strict';

document.addEventListener('DOMContentLoaded', function () {
  (function () {
    const chatContactsBody = document.querySelector('.app-chat-contacts .sidebar-body'),
      chatHistoryBody = document.querySelector('.chat-history-body'),
      chatSidebarLeftBody = document.querySelector('.app-chat-sidebar-left .sidebar-body'),
      chatSidebarRightBody = document.querySelector('.app-chat-sidebar-right .sidebar-body'),
      formSendMessage = document.querySelector('.form-send-message'),
      messageInput = document.querySelector('.message-input');

    // Initialize PerfectScrollbar
    // ------------------------------

    // Chat contacts scrollbar
    if (chatContactsBody) {
      new PerfectScrollbar(chatContactsBody, {
        wheelPropagation: false,
        suppressScrollX: true
      });
    }

    // Chat history scrollbar
    if (chatHistoryBody) {
      new PerfectScrollbar(chatHistoryBody, {
        wheelPropagation: false,
        suppressScrollX: true
      });
    }

    // Sidebar left scrollbar
    if (chatSidebarLeftBody) {
      new PerfectScrollbar(chatSidebarLeftBody, {
        wheelPropagation: false,
        suppressScrollX: true
      });
    }

    // Sidebar right scrollbar
    if (chatSidebarRightBody) {
      new PerfectScrollbar(chatSidebarRightBody, {
        wheelPropagation: false,
        suppressScrollX: true
      });
    }

    async function sendMessageToServer(message) {
      try {
        const response = await fetch('/api/chat/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            model: 'deepseek-r1:14b',
            messages: message,
          })
        });

        if (!response.ok) {
          throw new Error('Network response was not ok ' + response.statusText);
        }

        const jsonResponse = await response.json();
        
        // 处理服务器响应
        if (jsonResponse && typeof jsonResponse === 'object') {
          if (jsonResponse.success === true && typeof jsonResponse.message === 'string') {
            // 格式化消息内容，去除前导空行并将换行符转换为HTML换行
            const formattedMessage = jsonResponse.message.trim().replace(/\n/g, '<br>');
            
            // 更新对话框显示
            updateOrCreateServerMessage(formattedMessage);
            
            // 确保滚动到最新消息
            scrollToBottom();
          } else {
            console.warn('Invalid message format in response:', jsonResponse);
            updateOrCreateServerMessage('服务器返回的消息格式不正确');
          }
        } else {
          console.warn('Invalid response format from server:', jsonResponse);
          updateOrCreateServerMessage('服务器响应格式不正确');
        }
      } catch (error) {
        console.error('Error sending message:', error);
        // 显示错误消息给用户
        const errorMessage = '发送消息时出错，请稍后重试';
        updateOrCreateServerMessage(errorMessage);
      }
    }

    function updateOrCreateServerMessage(message) {
      const chatHistory = document.querySelector('ul.chat-history');
      const lastLi = chatHistory.querySelector('li:last-child');
      let serverMessageLi;

      if (lastLi && lastLi.classList.contains('chat-message-right')) {
        // 如果最后一个li是用户消息，创建一个新的li用于服务器消息
        serverMessageLi = document.createElement('li');
        serverMessageLi.classList.add('chat-message');
        chatHistory.appendChild(serverMessageLi);
      } else if (lastLi) {
        serverMessageLi = lastLi;
        // 清空现有内容
        serverMessageLi.innerHTML = '';
      } else {
        // 如果没有任何消息，创建第一个消息
        serverMessageLi = document.createElement('li');
        serverMessageLi.classList.add('chat-message');
        chatHistory.appendChild(serverMessageLi);
      }

      // 创建用户头像部分
      const userAvatarDiv = document.createElement('div');
      userAvatarDiv.className = 'user-avatar flex-shrink-0 me-4';
      const avatarDiv = document.createElement('div');
      avatarDiv.className = 'avatar avatar-sm';
      const avatarImg = document.createElement('img');
      avatarImg.src = '/static/img/ditan_logo.png';
      avatarImg.alt = 'Avatar';
      avatarImg.classList.add('rounded-circle');

      avatarDiv.appendChild(avatarImg);
      userAvatarDiv.appendChild(avatarDiv);

      // 创建消息内容结构
      const dFlexDiv = document.createElement('div');
      dFlexDiv.className = 'd-flex overflow-hidden';

      const chatMessageWrapperDiv = document.createElement('div');
      chatMessageWrapperDiv.className = 'chat-message-wrapper flex-grow-1';

      const renderMsg = document.createElement('div');
      renderMsg.className = 'chat-message-text mt-2';
      renderMsg.innerHTML = '<p class="mb-0 text-break">' + message + '</p>';

      chatMessageWrapperDiv.appendChild(renderMsg);
      dFlexDiv.appendChild(userAvatarDiv);
      dFlexDiv.appendChild(chatMessageWrapperDiv);
      serverMessageLi.appendChild(dFlexDiv);

      // 滚动到最新消息
      scrollToBottom();
    }

    // 显示消息的函数
    function displayMessage(message, messageClass) {
      let renderMsg = document.createElement('div');
      renderMsg.className = 'chat-message-text mt-2';
      renderMsg.innerHTML = '<p class="mb-0 text-break">' + message + '</p>';

      // Create the chat message wrapper and append the message
      let chatMessage = document.createElement('li');
      chatMessage.className = messageClass; // Apply the passed class (e.g., "chat-message" for the server response)

      let avatarWrapper = document.createElement('div');
      avatarWrapper.className = 'd-flex overflow-hidden';

      let chatMessageWrapper = document.createElement('div');
      chatMessageWrapper.className = 'chat-message-wrapper flex-grow-1';
      chatMessageWrapper.appendChild(renderMsg);

      avatarWrapper.appendChild(chatMessageWrapper);

      chatMessage.appendChild(avatarWrapper);

      // Append the new chat message to the last list item
      document.querySelector('ul.chat-history').appendChild(chatMessage);

      // Scroll to bottom
      scrollToBottom();
    }

    // Scroll to bottom function
    function scrollToBottom() {
      chatHistoryBody.scrollTo(0, chatHistoryBody.scrollHeight);
    }

    scrollToBottom();

    // Send Message
    formSendMessage.addEventListener('submit', e => {
      e.preventDefault();
      if (messageInput.value) {
        // Create a div and add a class
        displayMessage(messageInput.value, 'chat-message chat-message-right');
        sendMessageToServer(messageInput.value); // 调用发送消息的函数
        messageInput.value = '';
      }
    });

    // on click of chatHistoryHeaderMenu, Remove data-overlay attribute from chatSidebarLeftClose to resolve overlay overlapping issue for two sidebar
    let chatHistoryHeaderMenu = document.querySelector(".chat-history-header [data-target='#app-chat-contacts']"),
      chatSidebarLeftClose = document.querySelector('.app-chat-sidebar-left .close-sidebar');
    chatHistoryHeaderMenu.addEventListener('click', e => {
      chatSidebarLeftClose.removeAttribute('data-overlay');
    });
    // }
  })();
});

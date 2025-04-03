document.addEventListener('DOMContentLoaded', () => {
    const adsList = document.getElementById('ads-list');
    const updatedTimeElement = document.getElementById('updated-time'); // Select the element for updated time

    fetch('https://raw.githubusercontent.com/adrianskup/olx-parser/main/olx_ads.json')
        .then(response => response.json())
        .then(data => {
            console.log(data); // Печатаем данные в консоль, чтобы проверить их

            // Update the "last updated" timestamp
            if (updatedTimeElement) {
                updatedTimeElement.textContent = `Last updated: ${data.updated}`;
            }

            const ads = data.ads;
            adsList.innerHTML = '';

            ads.forEach(ad => {
                const adItem = document.createElement('div');
                adItem.classList.add('ad-item');

                // Добавляем картинку, если есть
                const imageUrl = ad.image_url ? ad.image_url : 'default-image.jpg';
                
                // Формируем блок с деталями авто
                let detailsHtml = '<div class="details">';
                if (ad.details) {
                    for (const [key, value] of Object.entries(ad.details)) {
                        detailsHtml += `<div><strong>${key}:</strong> ${value}</div>`;
                    }
                }
                detailsHtml += '</div>';

                // Проверяем, есть ли торг
                const negotiableText = ad.negotiable ? '<div class="negotiable">💰 Возможен торг</div>' : '';

                adItem.innerHTML = `
                    <img src="${imageUrl}" alt="Car Image">
                    <div class="content">
                        <div class="title"><a href="${ad.link}" target="_blank">${ad.title}</a></div>
                        <div class="price">${ad.price}</div>
                        ${negotiableText} <!-- Показываем "Возможен торг" только если negotiable = true -->
                        <div class="location">${ad.location}</div>
                        <div class="date">${ad.date}</div>
                        <div class="description">${ad.description}</div>
                        ${detailsHtml} <!-- Вставляем блок с деталями -->
                    </div>
                `;
                adsList.appendChild(adItem);
            });
        })
        .catch(error => {
            console.error("Error loading JSON:", error); // Печатаем ошибку в консоль
            adsList.innerHTML = 'Произошла ошибка при загрузке данных. Попробуйте позже.';
        });
});

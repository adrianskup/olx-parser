document.addEventListener('DOMContentLoaded', () => {
    const adsList = document.getElementById('ads-list');

    fetch('https://raw.githubusercontent.com/adrianskup/olx-parser/main/olx_ads.json')
        .then(response => response.json())
        .then(data => {
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

                adItem.innerHTML = `
                    <img src="${imageUrl}" alt="Car Image">
                    <div class="content">
                        <div class="title"><a href="${ad.link}" target="_blank">${ad.title}</a></div>
                        <div class="price">${ad.price}</div>
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
            adsList.innerHTML = 'Произошла ошибка при загрузке данных. Попробуйте позже.';
        });
});

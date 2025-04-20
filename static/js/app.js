// Orange News Scraper - Main Application JavaScript

// Global state
const state = {
    apiKey: localStorage.getItem('orangeNewsApiKey') || '',
    scrapedData: [],
    currentArticle: null,
    analyticsData: {
        sentiment: {},
        keywords: [],
        images: []
    },
    urls: []
};

// Document ready
$(document).ready(function() {
    console.log("Application initialized");
    
    // Check if API key exists
    if (!state.apiKey) {
        $('#apiKeyModal').modal('show');
    }
    
    // Setup event listeners
    setupEventListeners();
    
    // Initialize UI
    updateUrlList();
    
    // Update max workers range value display
    $('#max-workers').on('input', function() {
        $('#worker-value').text($(this).val());
    });
    
    // Update max length range value display
    $('#max-length').on('input', function() {
        $('#length-value').text($(this).val());
    });
    
    // Initialize template defaults
    updateTemplateDefaults();
});

// Setup event listeners
function setupEventListeners() {
    console.log("Setting up event listeners");
    
    // API Key Modal
    $('#save-api-key-btn').on('click', function() {
        console.log("API key button clicked");
        const apiKey = $('#api-key-input').val().trim();
        if (apiKey) {
            state.apiKey = apiKey;
            localStorage.setItem('orangeNewsApiKey', apiKey);
            $('#apiKeyModal').modal('hide');
        }
    });
    
    // URL Management
    $('#add-url-btn').on('click', function() {
        console.log("Add URL button clicked");
        addCustomUrl();
    });
    
    $('#clear-urls-btn').on('click', function() {
        console.log("Clear URLs button clicked");
        clearUrls();
    });
    
    $('#topic-select').on('change', function() {
        console.log("Topic changed");
        updateUrlsFromTopic();
    });
    
    // Scraping
    $('#start-scraping-btn').on('click', function() {
        console.log("Start scraping button clicked");
        startScraping();
    });
    
    // Article Generation
    $('#generate-form').on('submit', function(e) {
        console.log("Generate form submitted");
        e.preventDefault();
        generateArticle();
    });
    
    // Template Selection
    $('#template-select').on('change', function() {
        console.log("Template changed");
        updateTemplateDefaults();
    });
    
    // Download Buttons
    $('#download-md-btn').on('click', function() {
        console.log("Download MD button clicked");
        downloadArticle('md');
    });
    
    $('#download-html-btn').on('click', function() {
        console.log("Download HTML button clicked");
        downloadArticle('html');
    });
    
    $('#download-json-btn').on('click', function() {
        console.log("Download JSON button clicked");
        downloadArticle('json');
    });
    
    // Tab change event to refresh charts when analytics tab is shown
    $('button[data-bs-toggle="tab"]').on('shown.bs.tab', function (e) {
        const targetTab = $(e.target).attr('id');
        
        if (targetTab === 'analytics-tab') {
            // Redraw charts after tab is shown (fixes layout issues)
            setTimeout(() => {
                if (state.analyticsData.sentiment && Object.keys(state.analyticsData.sentiment).length > 0) {
                    // Redraw each sentiment gauge
                    Object.keys(state.analyticsData.sentiment).forEach(key => {
                        const gaugeDiv = document.getElementById(`gauge-${key}`);
                        if (gaugeDiv && gaugeDiv._fullData) {
                            Plotly.relayout(gaugeDiv, {autosize: true});
                        }
                    });
                }
                
                // Redraw keywords chart
                const keywordsDiv = document.getElementById('keywords-chart-container');
                if (keywordsDiv && keywordsDiv._fullData) {
                    Plotly.relayout(keywordsDiv, {autosize: true});
                }
            }, 100);
        }
    });
}

// Add custom URL
function addCustomUrl() {
    const url = $('#custom-url').val().trim();
    if (url && !state.urls.includes(url)) {
        state.urls.push(url);
        updateUrlList();
        $('#custom-url').val('');
    }
}

// Clear URLs
function clearUrls() {
    state.urls = [];
    updateUrlList();
}

// Update URLs from topic
function updateUrlsFromTopic() {
    const topic = $('#topic-select').val();
    console.log(`Updating URLs for topic: ${topic}`);
    
    // Get sources from server
    $.ajax({
        url: '/api/get_sources',
        type: 'GET',
        data: { topic: topic },
        success: function(response) {
            console.log("Got sources from server:", response);
            if (response.success) {
                state.urls = response.urls || [];
                updateUrlList();
            }
        },
        error: function(xhr, status, error) {
            console.error("Error getting sources:", error);
        }
    });
}

// Update URL list display
function updateUrlList() {
    const urlList = $('#url-list');
    urlList.empty();
    
    if (state.urls.length === 0) {
        urlList.html('<p class="text-muted">No URLs added. Select a topic or add custom URLs.</p>');
        return;
    }
    
    state.urls.forEach(url => {
        const urlBadge = $('<span></span>')
            .addClass('url-badge')
            .html(`${url} <button class="btn-close btn-close-sm remove-url" data-url="${url}"></button>`);
        urlList.append(urlBadge);
    });
    
    // Add event listener for remove buttons
    $('.remove-url').on('click', function() {
        const url = $(this).data('url');
        state.urls = state.urls.filter(u => u !== url);
        updateUrlList();
    });
}

// Start scraping
function startScraping() {
    console.log("Starting scraping process");
    
    if (!state.apiKey) {
        console.log("No API key found, showing modal");
        $('#apiKeyModal').modal('show');
        return;
    }
    
    // Get parameters
    const topic = $('#topic-select').val();
    const searchKeyword = $('#search-keyword').val().trim();
    const maxWorkers = $('#max-workers').val();
    
    console.log(`Scraping with topic: ${topic}, keyword: ${searchKeyword}, workers: ${maxWorkers}`);
    console.log(`URLs to scrape: ${state.urls}`);
    
    // Show loading overlay
    showLoading('Scraping news sources...');
    
    // Update UI
    $('#scraping-status').removeClass('alert-info alert-success alert-danger')
        .addClass('alert-warning')
        .html('<i class="fas fa-spinner fa-spin"></i> Scraping in progress...');
    
    $('#scraping-progress-container').show();
    $('#scraping-progress-bar').css('width', '30%');
    
    // Prepare request data
    const requestData = {
        api_key: state.apiKey,
        topic: topic,
        custom_urls: state.urls,
        search_keyword: searchKeyword,
        max_workers: parseInt(maxWorkers)
    };
    
    console.log("Sending request data:", JSON.stringify(requestData));
    
    // API request
    $.ajax({
        url: '/api/scrape',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(requestData),
        success: function(response) {
            console.log("Scraping successful:", response);
            hideLoading();
            
            // Update progress
            $('#scraping-progress-bar').css('width', '100%');
            
            // Update state
            state.scrapedData = response.results;
            
            // Update UI
            $('#scraping-status').removeClass('alert-warning alert-danger')
                .addClass('alert-success')
                .html(`<i class="fas fa-check-circle"></i> Successfully scraped ${response.total} articles.`);
            
            // Update table
            updateScrapedArticles();
            
            // After a delay, hide the progress bar
            setTimeout(function() {
                $('#scraping-progress-container').hide();
            }, 2000);
        },
        error: function(xhr, status, error) {
            console.error("Scraping error:", error);
            console.error("Response:", xhr.responseText);
            hideLoading();
            
            // Update UI
            $('#scraping-status').removeClass('alert-warning alert-success')
                .addClass('alert-danger')
                .html(`<i class="fas fa-exclamation-circle"></i> Error: ${xhr.responseJSON?.error || error}`);
            
            // Hide progress bar
            $('#scraping-progress-container').hide();
        }
    });
}

// Update scraped articles table
function updateScrapedArticles() {
    console.log("Updating scraped articles table");
    console.log("Scraped data:", state.scrapedData);
    
    const tbody = $('#articles-tbody');
    tbody.empty();
    
    if (!state.scrapedData || state.scrapedData.length === 0) {
        console.log("No scraped data found");
        $('#no-articles-message').show();
        $('#articles-table').hide();
        $('#article-count').text('0');
        return;
    }
    
    $('#no-articles-message').hide();
    $('#articles-table').show();
    
    let validCount = 0;
    
    state.scrapedData.forEach((article, index) => {
        if ('error' in article) {
            console.log(`Skipping article with error: ${article.error}`);
            return; // Skip articles with errors
        }
        
        validCount++;
        
        const title = article.title || 'Untitled';
        const source = article.url || '';
        const date = article.publish_date || 'Unknown';
        
        console.log(`Adding article: ${title}`);
        
        const row = $('<tr></tr>');
        row.html(`
            <td>${title}</td>
            <td><a href="${source}" target="_blank">${source.substring(0, 30)}...</a></td>
            <td>${date}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary view-article" data-index="${index}">
                    <i class="fas fa-eye"></i>
                </button>
            </td>
        `);
        
        tbody.append(row);
    });
    
    // Update article count
    $('#article-count').text(validCount);
    
    // Add event listener for view buttons
    $('.view-article').on('click', function() {
        const index = $(this).data('index');
        const article = state.scrapedData[index];
        
        // Show article in modal
        $('#preview-title').text(article.title || 'Untitled');
        $('#preview-date').text(article.publish_date || 'Unknown date');
        $('#preview-source').text(article.url || '');
        
        // Format content for better readability
        const formattedContent = article.content ? article.content.replace(/\n/g, '<br>') : 'No content available';
        $('#preview-content').html(formattedContent);
        
        // Show image if available
        if (article.image_url) {
            $('#preview-image').attr('src', article.image_url).show();
        } else {
            $('#preview-image').hide();
        }
        
        // Show the modal
        $('#articlePreviewModal').modal('show');
    });
}

// Update template defaults
function updateTemplateDefaults() {
    const template = $('#template-select').val();
    console.log(`Updating template defaults for: ${template}`);
    
    // Get template settings from server
    $.ajax({
        url: '/api/template_defaults',
        type: 'GET',
        data: { template: template },
        success: function(response) {
            console.log("Got template defaults:", response);
            if (response.success) {
                const templateDefaults = response.template || {};
                
                // Update form fields
                $('#custom-topic').val(templateDefaults.topic || '');
                $('#audience').val(templateDefaults.audience || '');
                $('#tone').val(templateDefaults.tone || '');
                
                if (templateDefaults.max_length) {
                    $('#max-length').val(templateDefaults.max_length);
                    $('#length-value').text(templateDefaults.max_length);
                }
            }
        },
        error: function(xhr, status, error) {
            console.error("Error getting template defaults:", error);
        }
    });
}

// Generate article
function generateArticle() {
    console.log("Generating article");
    
    if (!state.apiKey) {
        console.log("No API key found, showing modal");
        $('#apiKeyModal').modal('show');
        return;
    }
    
    if (!state.scrapedData || state.scrapedData.length === 0) {
        console.log("No scraped data available");
        $('#generation-status').removeClass('alert-info alert-success alert-warning')
            .addClass('alert-danger')
            .html('<i class="fas fa-exclamation-circle"></i> Error: No articles scraped. Please scrape articles first.');
        return;
    }
    
    // Get parameters
    const template = $('#template-select').val();
    const customTopic = $('#custom-topic').val().trim();
    const audience = $('#audience').val().trim();
    const tone = $('#tone').val().trim();
    const maxLength = $('#max-length').val();
    const includeImages = $('#include-images').is(':checked');
    
    console.log(`Generating with template: ${template}, topic: ${customTopic}, length: ${maxLength}`);
    
    // Show loading overlay
    showLoading('Generating article...');
    
    // Update UI
    $('#generation-status').removeClass('alert-info alert-success alert-danger')
        .addClass('alert-warning')
        .html('<i class="fas fa-spinner fa-spin"></i> Generating article...');
    
    $('#generation-progress-container').show();
    $('#generation-progress-bar').css('width', '30%');
    $('#generation-instructions').hide();
    
    // API request
    $.ajax({
        url: '/api/generate',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            api_key: state.apiKey,
            scraped_data: state.scrapedData,
            template: template,
            topic: customTopic,
            audience: audience,
            tone: tone,
            max_length: parseInt(maxLength),
            include_images: includeImages
        }),
        success: function(response) {
            console.log("Generation successful:", response);
            hideLoading();
            
            // Update progress
            $('#generation-progress-bar').css('width', '100%');
            
            // Check if response format is valid
            if (!response.article || typeof response.article.content === 'undefined') {
                console.error("Invalid response format:", response);
                $('#generation-status').removeClass('alert-warning alert-success')
                    .addClass('alert-danger')
                    .html('<i class="fas fa-exclamation-circle"></i> Error: Invalid response from server');
                
                $('#generation-progress-container').hide();
                return;
            }
            
            // Update state with response data
            state.currentArticle = response.article;
            
            // Make sure analytics data is properly extracted and formatted
            state.analyticsData = {
                sentiment: response.article.sentiment_analysis || {},
                keywords: Array.isArray(response.article.keywords) ? response.article.keywords : [],
                images: Array.isArray(response.article.images) ? response.article.images : []
            };
            
            console.log("Updated state:", state);
            
            // Update UI
            $('#generation-status').removeClass('alert-warning alert-danger')
                .addClass('alert-success')
                .html('<i class="fas fa-check-circle"></i> Article generated successfully!');
            
            // Update article preview with the content and HTML
            updateArticlePreview(response.article.content, response.html_content);
            
            // Update analytics
            updateAnalytics();
            
            // After a delay, hide the progress bar
            setTimeout(function() {
                $('#generation-progress-container').hide();
            }, 2000);
            
            // Switch to results tab
            $('#results-tab').tab('show');
        },
        error: function(xhr, status, error) {
            console.error("Generation error:", error);
            console.error("Response:", xhr.responseText);
            hideLoading();
            
            // Update UI
            $('#generation-status').removeClass('alert-warning alert-success')
                .addClass('alert-danger')
                .html(`<i class="fas fa-exclamation-circle"></i> Error: ${xhr.responseJSON?.error || error}`);
            
            // Hide progress bar
            $('#generation-progress-container').hide();
        }
    });
}

// Update article preview
function updateArticlePreview(markdown, html) {
    console.log("Updating article preview");
    console.log("Markdown content length:", markdown ? markdown.length : 0);
    console.log("HTML content length:", html ? html.length : 0);
    
    if (!markdown) {
        console.log("No markdown content to preview");
        $('#no-article-message').show();
        $('#article-text').parent().hide();
        $('#preview-tabs').hide();
        $('#preview-content').hide();
        return;
    }
    
    $('#no-article-message').hide();
    $('#article-text').parent().show();
    $('#preview-tabs').show();
    $('#preview-content').show();
    
    // Update markdown preview
    $('#article-text').val(markdown);
    
    // Update HTML preview
    if (html) {
        $('#article-html-preview').html(html);
    } else if (typeof marked !== 'undefined') {
        // Use marked.js to convert markdown to HTML if available
        $('#article-html-preview').html(marked.parse(markdown));
    } else {
        // Simple fallback for markdown conversion
        let htmlContent = markdown
            .replace(/# (.*)/g, '<h1>$1</h1>')
            .replace(/## (.*)/g, '<h2>$1</h2>')
            .replace(/### (.*)/g, '<h3>$1</h3>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        htmlContent = '<p>' + htmlContent + '</p>';
        $('#article-html-preview').html(htmlContent);
    }
    
    // Calculate statistics
    const wordCount = markdown.split(/\s+/).filter(word => word.length > 0).length;
    const charCount = markdown.length;
    const lineCount = markdown.split('\n').length;
    
    // Update statistics
    $('#word-count').text(wordCount);
    $('#char-count').text(charCount);
    $('#line-count').text(lineCount);
    
    // Show statistics
    $('#no-stats-message').hide();
    $('#stats-container').show();
}

// Update analytics
function updateAnalytics() {
    console.log("Updating analytics");
    console.log("Analytics data:", state.analyticsData);
    
    // Update sentiment gauges
    updateSentimentGauges();
    
    // Update keywords
    updateKeywords();
    
    // Update images
    updateImages();
}

// Update sentiment gauges
function updateSentimentGauges() {
    console.log("Updating sentiment gauges");
    
    const sentimentData = state.analyticsData.sentiment;
    const container = $('#sentiment-gauges');
    container.empty();
    
    console.log("Sentiment data:", sentimentData);
    
    if (!sentimentData || Object.keys(sentimentData).length === 0) {
        console.log("No sentiment data available");
        $('#no-sentiment-message').show();
        return;
    }
    
    $('#no-sentiment-message').hide();
    
    // Create a gauge for each sentiment score
    Object.entries(sentimentData).forEach(([key, value]) => {
        console.log(`Creating gauge for ${key}: ${value}`);
        
        if (typeof value === 'number') {
            // Convert sentiment score to a 0-100 scale
            const gaugeValue = (value + 1) * 50;
            
            // Create gauge container
            const gaugeContainer = $('<div></div>')
                .addClass('sentiment-gauge')
                .attr('id', `gauge-${key}`);
            
            container.append(gaugeContainer);
            
            // Create gauge using Plotly
            try {
                const data = [{
                    type: 'indicator',
                    mode: 'gauge+number',
                    value: gaugeValue,
                    title: { text: key.replace(/_/g, ' ').toUpperCase() },
                    gauge: {
                        axis: { range: [0, 100], tickcolor: '#333' },
                        bar: { color: '#FF7900' },
                        bgcolor: 'white',
                        borderwidth: 2,
                        bordercolor: '#CCCCCC',
                        steps: [
                            { range: [0, 33], color: '#FF6B6B' },  // Negative
                            { range: [33, 66], color: '#FFD166' }, // Neutral
                            { range: [66, 100], color: '#06D6A0' } // Positive
                        ],
                        threshold: {
                            line: { color: 'black', width: 4 },
                            thickness: 0.75,
                            value: gaugeValue
                        }
                    }
                }];
                
                const layout = {
                    height: 200,
                    margin: { t: 30, r: 30, l: 30, b: 0 },
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    font: { family: 'Arial, sans-serif' }
                };
                
                const config = {
                    responsive: true,
                    displayModeBar: false
                };
                
                Plotly.newPlot(`gauge-${key}`, data, layout, config);
                console.log(`Gauge for ${key} created successfully`);
            } catch (error) {
                console.error(`Error creating gauge for ${key}:`, error);
                // Show error message in gauge container
                gaugeContainer.html(`<div class="alert alert-danger">Error creating gauge for ${key}</div>`);
            }
        }
    });
}

// Update keywords
function updateKeywords() {
    console.log("Updating keywords");
    
    const keywords = state.analyticsData.keywords;
    const container = $('#keywords-container');
    container.empty();
    
    console.log("Keywords:", keywords);
    
    if (!keywords || !Array.isArray(keywords) || keywords.length === 0) {
        console.log("No keywords available");
        $('#no-keywords-message').show();
        $('#keywords-chart-container').hide();
        return;
    }
    
    $('#no-keywords-message').hide();
    $('#keywords-chart-container').show();
    
    // Create keyword tags
    keywords.forEach(keyword => {
        if (keyword && typeof keyword === 'string') {
            const tag = $('<span></span>')
                .addClass('keyword-tag')
                .text(keyword);
            container.append(tag);
        }
    });
    
    // Create keyword chart
    try {
        // Display up to 10 keywords for better visualization
        const displayKeywords = keywords.slice(0, 10);
        // Create relevance score (descending from most to least important)
        const keywordValues = displayKeywords.map((_, i) => displayKeywords.length - i);
        
        const chartData = [{
            x: keywordValues,
            y: displayKeywords,
            type: 'bar',
            orientation: 'h',
            marker: {
                color: '#FF7900',
                opacity: 0.8
            }
        }];
        
        const layout = {
            height: 300,
            margin: { t: 10, r: 10, l: 120, b: 50 },
            xaxis: {
                title: 'Relevance',
                showgrid: true,
                gridcolor: '#f0f0f0'
            },
            yaxis: {
                automargin: true
            },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { family: 'Arial, sans-serif' }
        };
        
        const config = {
            responsive: true,
            displayModeBar: false
        };
        
        Plotly.newPlot('keywords-chart-container', chartData, layout, config);
        console.log("Keywords chart created successfully");
    } catch (error) {
        console.error("Error creating keywords chart:", error);
        // Show error message in chart container
        $('#keywords-chart-container').html('<div class="alert alert-danger">Error creating keywords chart</div>');
    }
}

// Update images
function updateImages() {
    console.log("Updating images");
    
    const images = state.analyticsData.images;
    const container = $('#images-container');
    container.empty();
    
    console.log("Images:", images);
    
    if (!images || !Array.isArray(images) || images.length === 0) {
        console.log("No images available");
        $('#no-images-message').show();
        return;
    }
    
    $('#no-images-message').hide();
    
    // Create image cards with better error handling
    images.forEach(image => {
        if (image && image.url) {
            const truncatedTitle = image.title && image.title.length > 30 ? 
                                  image.title.substring(0, 30) + '...' : 
                                  (image.title || 'Image');
            
            const truncatedSource = image.source && image.source.length > 30 ? 
                                   image.source.substring(0, 30) + '...' : 
                                   (image.source || '#');
            
            const imageCard = $('<div></div>')
                .addClass('col-md-3 mb-3')
                .html(`
                    <div class="card h-100 shadow-sm">
                        <div class="card-img-top" style="height: 150px; background-color: #f8f9fa; display: flex; align-items: center; justify-content: center;">
                            <img src="${image.url}" alt="${truncatedTitle}" style="max-height: 100%; max-width: 100%; object-fit: contain;" onerror="this.onerror=null; this.src='https://via.placeholder.com/300x200?text=Image+Unavailable'; this.style.opacity=0.5;">
                        </div>
                        <div class="card-body">
                            <p class="card-text small" title="${image.title || ''}">${truncatedTitle}</p>
                            <a href="${image.source}" target="_blank" class="btn btn-sm btn-outline-secondary" title="${image.source || ''}">Source</a>
                        </div>
                    </div>
                `);
            container.append(imageCard);
        }
    });
}

// Download article
function downloadArticle(format) {
    console.log(`Downloading article in ${format} format`);
    
    if (!state.currentArticle || !state.currentArticle.content) {
        alert('No article to download. Please generate an article first.');
        return;
    }
    
    // Show loading overlay
    showLoading('Preparing download...');
    
    // Prepare data for download
    const content = state.currentArticle.content;
    const template = $('#template-select').val() || 'article';
    let analyticsData = {};
    
    if (format === 'json') {
        // Prepare analytics data
        analyticsData = {
            article_info: {
                title: template,
                date: new Date().toISOString(),
                word_count: content.split(/\s+/).filter(word => word.length > 0).length
            },
            sentiment: state.analyticsData.sentiment,
            keywords: state.analyticsData.keywords,
            images: state.analyticsData.images.map(img => ({
                url: img.url,
                title: img.title || '',
                source: img.source || ''
            }))
        };
    }
    
    // API request
    $.ajax({
        url: '/api/download',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            content: content,
            format: format,
            template_name: template,
            analytics_data: analyticsData
        }),
        success: function(response) {
            console.log("Download preparation successful:", response);
            hideLoading();
            
            if (!response.success || !response.content) {
                console.error("Invalid download response:", response);
                alert('Error preparing download. Please try again.');
                return;
            }
            
            // Create download link
            const downloadUrl = response.download_url + '?content=' + encodeURIComponent(response.content);
            
            // Create a temporary link element and trigger download
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = response.filename || `orange_article.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            
            // Show success message
            const formatName = format === 'md' ? 'Markdown' : 
                              format === 'html' ? 'HTML' : 'JSON';
            
            const successAlert = $(`<div class="alert alert-success alert-dismissible fade show mt-3" role="alert">
                <i class="fas fa-check-circle"></i> ${formatName} file downloaded successfully!
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>`);
            
            $('#results').prepend(successAlert);
            
            // Auto remove alert after 5 seconds
            setTimeout(() => {
                successAlert.alert('close');
            }, 5000);
        },
        error: function(xhr, status, error) {
            console.error("Download error:", error);
            console.error("Response:", xhr.responseText);
            hideLoading();
            alert(`Error preparing download: ${xhr.responseJSON?.error || error}`);
        }
    });
}

// Show loading overlay
function showLoading(message) {
    $('#loading-message').text(message || 'Processing...');
    $('#loading-overlay').show();
}

// Hide loading overlay
function hideLoading() {
    $('#loading-overlay').hide();
}
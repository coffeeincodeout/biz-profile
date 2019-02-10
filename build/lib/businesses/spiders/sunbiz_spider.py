import scrapy
from scrapy.exceptions import CloseSpider

import os
import sys


class SunbizSpider(scrapy.Spider):
    name = 'sunbiz'
    start_urls = [
        'http://search.sunbiz.org/Inquiry/CorporationSearch/SearchResults?InquiryType=EntityName&inquiryDirectionType=PreviousList&searchNameOrder=AZZURRA%20L180002355061&SearchTerm=b&entityId=L18000235506&listNameOrder=AZZURRA%20L180002355061',
        # 'http://search.sunbiz.org/Inquiry/CorporationSearch/SearchResults?InquiryType=EntityName&inquiryDirectionType=PreviousList&searchNameOrder=A%20T082930&SearchTerm=a&entityId=T08293&listNameOrder=A%20T082930'
    ]

    TMP_FILE = os.path.join(os.path.dirname(sys.modules['businesses'].__file__), 'tmp/companies2.csv')
    custom_settings = {
        'FEED_FORMAT': 'csv',
        'FEED_URI': TMP_FILE,
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 2,
    }

    def parse(self, response):
        # get a list of all url and their status
        status_list = response.css('tr > td.small-width::text').extract()
        company_profile_link_list = response.css(
            '#search-results > table > tbody > tr > td.large-width > a::attr(href)').extract()
        company_name_list = response.css('#search-results > table > tbody > tr > td.large-width > a::text').extract()

        # loop through both lists and get the urls that are active
        for active, link, company_name in zip(status_list, company_profile_link_list, company_name_list):
            if active.lower() == 'active' and company_name[0].lower() == 'a':
                company_profile_link = response.urljoin(link)
                yield scrapy.Request(company_profile_link, callback=self.company_parse)
            elif company_name[0].lower() == 'b' or company_name.lower() == 'corporation b':
                # end script once companies that start with B
                raise CloseSpider('A search is complete')
            else:
                pass
        # get the next page link
        link = response.css(
            '#maincontent > div:nth-child(4) > div.navigationBarPaging > span:nth-child(2) > a::attr(href)')\
            .extract_first()
        # create the full url
        pagination = response.urljoin(link)
        yield scrapy.Request(pagination, callback=self.parse)

    def company_parse(self, response):
        company_list = response.css(
            '#maincontent > div.searchResultDetail > div.detailSection.corporationName > p::text').extract()
        filing_information = response.css(
            '#maincontent > div.searchResultDetail > div.detailSection.filingInformation > span:nth-child(2) > div > '
            'span::text').extract()
        labels_filing_information = response.css(
            '#maincontent > div.searchResultDetail > div.detailSection.filingInformation > span:nth-child(2) > div > '
            'label::text').extract()
        principal_address = response.css(
            '#maincontent > div.searchResultDetail > div:nth-child(4) > span:nth-child(2) > div::text').re('[^\r\n].+')
        address = [line.strip() for line in principal_address]

        company_info_dict = {
            'profile url': response.url,
            'company type': company_list[0],
            'company name': company_list[1],
            'principal address': " ".join(address),
        }

        for label, filing in zip(labels_filing_information, filing_information):
            company_info_dict.update({label: filing})

        yield company_info_dict


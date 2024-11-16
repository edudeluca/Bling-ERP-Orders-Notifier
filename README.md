# Bling-ERP-Orders-Notifier

## Description
TODO: describe program purpose and general logic

## TO-DO (improvements and features for future releases)
- [ ] save all the logs on the `logs` folder, making the root folder cleaner
- [ ] use environment variables for infomation related to the API authentication
- [ ] auto create json files, following the pre-defined structure
- [ ] read params files from `params` folder 
- [ ] use a single function for creating notification for both new and late orders
    - This'll make it easier to add notification customization, change sound for different orders situations (like if it still needs to be reserved, or if it just need to be packed)
- [ ] optimize requests while increasing monitoring (currently it scans only the last 100 orders, which represents bling's first page) and improving performance